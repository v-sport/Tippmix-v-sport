import json

# Nyisd meg a poller kimenetet
with open("poller_output.json", "r") as f:
    rounds = {}  # Forduló -> lista a meccsekről

    for line in f:
        if line.strip() == "":
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Ellenőrzés, van-e forduló adat
        round_number = None
        if 'round' in data:
            round_number = data['round']
        elif 'matchday' in data:
            round_number = data['matchday']
        else:
            round_number = f"Unknown ({data.get('competition_id', 'N/A')})"

        # Meccs leírása
        match_info = f"{data.get('home_team', 'Haza')} vs {data.get('away_team', 'Vendég')} at {data.get('start_time', 'N/A')}"

        # Hozzáadás a fordulóhoz
        if round_number not in rounds:
            rounds[round_number] = []
        rounds[round_number].append(match_info)

# Kiírás
for rnd, matches in rounds.items():
    print(f"\n=== Forduló {rnd} ===")
    for m in matches:
        print(m)