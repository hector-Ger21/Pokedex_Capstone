import psycopg2
import pandas as pd
import ast

# ─────────────────────────────────────────────────────────────
# Database connection
# ─────────────────────────────────────────────────────────────
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    dbname="Capstone testing",
    user="postgres",
    password="Goku21"
)
cursor = conn.cursor()

# ─────────────────────────────────────────────────────────────
# Load CSV file
# ─────────────────────────────────────────────────────────────
df = pd.read_csv(r'C:\Users\watta\Downloads\printables\pokemon.csv')

# Helper function to handle NaNs
def get(val):
    return val if pd.notna(val) else None

# ─────────────────────────────────────────────────────────────
# Insert into 'types' and 'abilities' tables
# ─────────────────────────────────────────────────────────────
type_set = set(df['type1'].dropna().unique()) | set(df['type2'].dropna().unique())
ability_set = set()

for abilities in df['abilities']:
    try:
        parsed = ast.literal_eval(abilities)
        ability_set.update(parsed)
    except:
        continue

type_id_map = {}
for t in type_set:
    cursor.execute("INSERT INTO types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;", (t,))
    result = cursor.fetchone()
    if result:
        type_id_map[t] = result[0]
    else:
        cursor.execute("SELECT id FROM types WHERE name = %s;", (t,))
        type_id_map[t] = cursor.fetchone()[0]

ability_id_map = {}
for a in ability_set:
    cursor.execute("INSERT INTO abilities (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;", (a,))
    result = cursor.fetchone()
    if result:
        ability_id_map[a] = result[0]
    else:
        cursor.execute("SELECT id FROM abilities WHERE name = %s;", (a,))
        ability_id_map[a] = cursor.fetchone()[0]

# ─────────────────────────────────────────────────────────────
# Insert Pokémon data into all relational tables
# ─────────────────────────────────────────────────────────────
for _, row in df.iterrows():
    pokedex_number = get(row['pokedex_number'])

    # Insert into pokedex
    cursor.execute("""
        INSERT INTO pokedex (pokedex_number, name, japanese_name, classfication, generation, is_legendary)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (pokedex_number) DO NOTHING;
    """, (
        pokedex_number,
        get(row['name']),
        get(row['japanese_name']),
        get(row['classfication']),
        get(row['generation']),
        bool(row['is_legendary'])
    ))

    # Insert into stats
    cursor.execute("""
        INSERT INTO stats (pokedex_number, hp, attack, defense, sp_attack, sp_defense, speed, base_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (pokedex_number) DO NOTHING;
    """, (
        pokedex_number,
        get(row['hp']),
        get(row['attack']),
        get(row['defense']),
        get(row['sp_attack']),
        get(row['sp_defense']),
        get(row['speed']),
        get(row['base_total'])
    ))

    # Insert into physical_info
    cursor.execute("""
        INSERT INTO physical_info (pokedex_number, height_m, weight_kg, capture_rate, base_egg_steps, base_happiness, percentage_male)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (pokedex_number) DO NOTHING;
    """, (
        pokedex_number,
        get(row['height_m']),
        get(row['weight_kg']),
        get(row['capture_rate']),
        get(row['base_egg_steps']),
        get(row['base_happiness']),
        get(row['percentage_male'])
    ))

    # Insert into effectiveness
    effectiveness_columns = [col for col in df.columns if col.startswith("against_")]
    effectiveness_values = [get(row[col]) for col in effectiveness_columns]
    
    cursor.execute(f"""
        INSERT INTO effectiveness (pokedex_number, {', '.join(effectiveness_columns)})
        VALUES (%s, {', '.join(['%s'] * len(effectiveness_columns))})
        ON CONFLICT (pokedex_number) DO NOTHING;
    """, (pokedex_number, *effectiveness_values))

    # Insert into pokemon_types
    if pd.notna(row['type1']):
        cursor.execute("""
            INSERT INTO pokemon_types (pokedex_number, type_id, slot)
            VALUES (%s, %s, 1)
            ON CONFLICT DO NOTHING;
        """, (pokedex_number, type_id_map[row['type1']]))
    if pd.notna(row['type2']):
        cursor.execute("""
            INSERT INTO pokemon_types (pokedex_number, type_id, slot)
            VALUES (%s, %s, 2)
            ON CONFLICT DO NOTHING;
        """, (pokedex_number, type_id_map[row['type2']]))

    # Insert into pokemon_abilities
    try:
        abilities = ast.literal_eval(row['abilities'])
        for ability in abilities:
            cursor.execute("""
                INSERT INTO pokemon_abilities (pokedex_number, ability_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, (pokedex_number, ability_id_map[ability]))
    except:
        continue

# ─────────────────────────────────────────────────────────────
# Finalize
# ─────────────────────────────────────────────────────────────
conn.commit()
cursor.close()
conn.close()

print("✅ Data successfully loaded into the schema.")
