# Import required libraries for the project
import ollama  # For interacting with the Ollama model
import psycopg2  # For connecting to PostgreSQL database
import re  # For handling regular expressions (if needed for future improvements)
import tkinter as tk  # For GUI creation
from tkinter import scrolledtext  # For implementing scrollable text area
from PIL import Image, ImageTk  # For handling Pokémon images
import requests  # For sending HTTP requests to fetch images from PokeAPI

# Define model name for Ollama-based AI
MODEL_NAME = 'mistral'  # You can switch to other models like 'llama3', 'sqlcoder', etc.

# PostgreSQL database configuration parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'Capstone testing',
    'user': 'postgres',
    'password': 'Goku21'
}

# Full Pokémon database schema creation string for PostgreSQL
SCHEMA = """
-- Main Pokémon table: Contains primary information for each Pokémon
CREATE TABLE pokedex (
    pokedex_number INTEGER PRIMARY KEY,
    name TEXT,
    japanese_name TEXT,
    classfication TEXT,
    generation INTEGER,
    is_legendary BOOLEAN
);

-- Stats table: Holds statistical data for each Pokémon
CREATE TABLE stats (
    pokedex_number INTEGER PRIMARY KEY REFERENCES pokedex(pokedex_number) ON DELETE CASCADE,
    hp INTEGER,
    attack INTEGER, 
    defense INTEGER,
    sp_attack INTEGER,
    sp_defense INTEGER,
    speed INTEGER,
    base_total INTEGER
);

-- Physical information table: Stores data about Pokémon's size, weight, and other physical attributes
CREATE TABLE physical_info (
    pokedex_number INTEGER PRIMARY KEY REFERENCES pokedex(pokedex_number) ON DELETE CASCADE,
    height_m DOUBLE PRECISION,
    weight_kg DOUBLE PRECISION,
    capture_rate TEXT,
    base_egg_steps INTEGER,
    base_happiness INTEGER,
    percentage_male DOUBLE PRECISION
);

-- Types table: Contains unique types such as Grass, Fire, Water, etc.
CREATE TABLE types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

-- Junction table: Pokémon and types (many-to-many relationship)
CREATE TABLE pokemon_types (
    pokedex_number INTEGER REFERENCES pokedex(pokedex_number) ON DELETE CASCADE,
    type_id INTEGER REFERENCES types(id) ON DELETE CASCADE,
    slot INTEGER CHECK (slot IN (1, 2)),
    PRIMARY KEY (pokedex_number, slot)
);

-- Abilities table: Contains Pokémon abilities like Overgrow, Levitate, etc.
CREATE TABLE abilities (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE
);

-- Junction table: Pokémon and abilities (many-to-many relationship)
CREATE TABLE pokemon_abilities (
    pokedex_number INTEGER REFERENCES pokedex(pokedex_number) ON DELETE CASCADE,
    ability_id INTEGER REFERENCES abilities(id) ON DELETE CASCADE,
    PRIMARY KEY (pokedex_number, ability_id)
);

-- Type effectiveness table: Stores type effectiveness for each Pokémon
CREATE TABLE effectiveness (
    pokedex_number INTEGER PRIMARY KEY REFERENCES pokedex(pokedex_number) ON DELETE CASCADE,
    against_bug DOUBLE PRECISION,
    against_dark DOUBLE PRECISION,
    against_dragon DOUBLE PRECISION,
    against_electric DOUBLE PRECISION,
    against_fairy DOUBLE PRECISION,
    against_fight DOUBLE PRECISION,
    against_fire DOUBLE PRECISION,
    against_flying DOUBLE PRECISION,
    against_ghost DOUBLE PRECISION,
    against_grass DOUBLE PRECISION,
    against_ground DOUBLE PRECISION,
    against_ice DOUBLE PRECISION,
    against_normal DOUBLE PRECISION,
    against_poison DOUBLE PRECISION,
    against_psychic DOUBLE PRECISION,
    against_rock DOUBLE PRECISION,
    against_steel DOUBLE PRECISION,
    against_water DOUBLE PRECISION
);
"""

# Function to fetch all Pokémon names from the database
def fetch_pokemon_names_from_db() -> list:
    """Fetch all Pokémon names from the database and convert them to lowercase for easy querying."""
    sql_query = "SELECT name FROM pokedex;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                rows = cur.fetchall()
                return [row[0].lower() for row in rows]  # Return names in lowercase for case-insensitive comparison
    except Exception as e:
        print(f"Error fetching Pokémon names: {e}")
        return []

# Function to convert user question into a SQL query using Ollama
def question_to_sql(question: str, model: str = MODEL_NAME) -> str:
    """Convert a natural language question into a valid SQL query for PostgreSQL."""
    prompt = f"""
You are a helpful assistant that converts user questions into **PostgreSQL-compatible** SQL queries.

 STRICT RULES:
- Always use table-qualified columns when there are joins (e.g., pokedex.name, stats.speed).
- When aliasing column output, write it as: actual_column AS "Descriptive Label"
     Example: stats.speed AS "Treecko's Speed"
     DO NOT write: "Treecko's Speed" AS speed
- Do not use ambiguous column names — always specify the table (e.g., pokedex.name NOT just name).
- Each query must focus on only one value (like speed, type, etc.).
- Return both type slots (slot 1 and 2) **only if** the user does not ask specifically for "type one" or "primary".

Schema:
{SCHEMA}

Question: "{question}"

Output only valid PostgreSQL SQL queries (no explanations, no markdown).
"""
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content'].strip()

# Function to run a SQL query on the PostgreSQL database
def run_sql_query(sql_query: str) -> list:
    """Execute the SQL query on the database and return the results."""
    results = []
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                try:
                    rows = cur.fetchall()
                except psycopg2.ProgrammingError:
                    rows = ["(Query ran, no result)"]  # Handle cases with no results
                results.append((sql_query, rows))
    except Exception as e:
        results.append(("ERROR", str(e)))
    return results

# Function to interpret SQL query results using the AI model
def interpret_results_with_ai(sql_results: list, question: str, model: str = MODEL_NAME) -> str:
    """Interpret SQL query results in the style of the Pokémon anime series Pokédex."""
    prompt = f"""
You are a virtual Pokédex from the Pokémon anime series. Summarize the query results below using a concise and factual tone.

📌 STRICT RULES:
- ONLY describe information present in the SQL query results.
- DO NOT add or invent extra facts.
- DO NOT speculate or soften facts (e.g., do not say "may exhibit", "sometimes", or "in some cases").
- If two types are returned, state them directly: "Type: Grass, Poison."
- DO NOT mention SQL, databases, or the query structure.
- DO NOT reference fields that were not part of the query.
- Use Pokédex-style narration (e.g., "Treecko. Speed: 70. Type: Grass.")

🧜‍♀️ Original Question: "{question}"

📊 SQL Results:
"""
    for q, rows in sql_results:
        prompt += f"\nQuery:\n{q}\nResults:\n{rows}\n"

    prompt += "\nPlease respond only using facts from the results, in the voice of the Pokédex."

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content'].strip()

# Function to fetch a Pokémon's image from PokeAPI
def fetch_pokemon_image(pokemon_name: str) -> Image.Image:
    """Fetch and return a Pokémon's sprite image from PokeAPI."""
    url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        sprite_url = data['sprites']['front_default']
        image = Image.open(requests.get(sprite_url, stream=True).raw)
        return image
    return None

# Welcome message for the user when they launch the Pokédex
def welcome_message():
    """Returns a welcome message detailing what the user can ask the Pokédex."""
    return ("\U0001f44b Hello! I'm your virtual Pokédex, here to help you learn about Pokémon!\n"
            "I can provide you with various facts, including:\n"
            "\U0001f9ec Abilities\n"
            "Typing (e.g., Fire, Water, Grass, etc.)\n"
            "\U0001f4ca Stats (e.g., Speed, Attack, etc.)\n"
            "\U0001f4cf Physical info \n"
            "\U0001f4e3 Pokedex Information \n"
            "\nFeel free to ask me anything! For Physical info, you can only ask about the following fields:\n"
            "- height_m (Height in meters)\n"
            "- weight_kg (Weight in kilograms)\n"
            "- capture_rate (Capture rate)\n"
            "- base_egg_steps (Egg steps)\n"
            "- base_happiness (Base happiness)\n\n"
            "\nFor Pokedex-related questions, you can only ask about the following fields:\n"
            "- Japanese name\n"
            "- Generation\n"
            "- Legendary status \n"
            "- Classification\n"
            "- Pokedex number\n\n"
            "⚠️ Important note: The more questions you ask, the harder it becomes for me to answer.\n"
            "I'm an older model Pokédex, so while I try my best, some complex questions might be more difficult for me to handle.\n")

# GUI Code: Creating the user interface with Tkinter

def on_submit():
    """Handles user input, generates SQL queries, runs them, and displays results."""
    question = entry.get()
    if question.lower() == 'exit':
        root.destroy()
        return

    output.delete('1.0', tk.END)

    # Generate the SQL query based on the user input question
    sql_query = question_to_sql(question)
    output.insert(tk.END, f"\n\U0001f4dc Generated SQL Query:\n{sql_query}\n")

    # Execute the SQL query and get the results
    results = run_sql_query(sql_query)
    for q, rows in results:
        output.insert(tk.END, f"\n\U0001f4ca Query Results:\n{rows}\n")

    # Interpret the results in a Pokédex-style summary
    interpretation = interpret_results_with_ai(results, question)
    output.insert(tk.END, f"\n\U0001f9e0 Pokédex Interpretation:\n{interpretation}\n")

    # Attempt to fetch and display the Pokémon image if it's part of the query
    pokemon_names = fetch_pokemon_names_from_db()
    matched_pokemon = next((name for name in pokemon_names if name in question.lower()), None)

    if matched_pokemon:
        pokemon_image = fetch_pokemon_image(matched_pokemon)
        if pokemon_image:
            pokemon_image.thumbnail((150, 150))  # Resize image to fit in the UI
            img_tk = ImageTk.PhotoImage(pokemon_image)

            # Display the image in the GUI
            panel.config(image=img_tk)
            panel.image = img_tk  # Maintain reference to the image to prevent garbage collection

    # Log the query and its results to a log file for debugging or record-keeping
    with open("query_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"Q: {question}\nSQL: {sql_query}\nResults: {results}\n---\n")

# Tkinter GUI setup
root = tk.Tk()
root.title("Virtual Pokédex")

# Frame for Pokémon Image and Text Output
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

# Pokémon Image Section (on the left side)
panel = tk.Label(frame)
panel.grid(row=0, column=0, padx=10, pady=10)

# Text Section (on the right side)
output_frame = tk.Frame(frame)
output_frame.grid(row=0, column=1, padx=10, pady=10)

# Display welcome message in the GUI
welcome_label = tk.Label(output_frame, text=welcome_message(), justify='left')
welcome_label.pack(padx=10, pady=10)

# User input entry and submit button for queries
entry = tk.Entry(output_frame, width=80)
entry.pack(padx=10, pady=5)

submit_btn = tk.Button(output_frame, text="Ask!", command=on_submit)
submit_btn.pack(padx=10, pady=5)

# Output display area with scrolling capability
output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=100, height=30)
output.pack(padx=10, pady=10)

# Run the Tkinter GUI event loop
root.mainloop()
