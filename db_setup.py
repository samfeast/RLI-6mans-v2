import os
import sqlite3


def create_blank_db():
    con = sqlite3.connect("database/database.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE accounts(id, platform, platform_id)")
    cur.execute("CREATE TABLE reminders(id, type, interval, message_type)")
    cur.execute(
        "CREATE TABLE player_data(id, tier, series_played, series_won, series_lost, points, elo)"
    )
    cur.execute(
        """CREATE TABLE game_log(
            game_id, status, 
            created_timestamp, reported_timestamp, 
            tier, team_type, 
            t1_p1, t1_p2, t1_p3, t2_p1, t2_p2, t2_p3, 
            winning_team, losing_team, p1_win, p2_win, 
            elo_swing, timeout_immunity)"""
    )
    con.commit()


if os.path.exists("database/database.db"):
    confirmation = input(
        "database.db already exists. Type 'Y' to delete it and create a new, blank database: "
    )
    if confirmation.lower() == "y":
        os.remove("database/database.db")
        create_blank_db()
else:
    create_blank_db()
