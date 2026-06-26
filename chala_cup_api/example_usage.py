"""
Script de Demostración del SDK de Chala Cup Club
"""

import sys
from chala_cup_api import ChalaCupClient, ChalaCupAPIError

def run_demo():
    print("[*] Conectando a https://chala-cup-club.vercel.app/ ...")
    client = ChalaCupClient()

    try:
        state = client.get_bootstrap()
        stats = client.get_general_stats()

        print("\n[+] Conexión exitosa con el Backend Vercel!")
        print(f"    Torneo        : CHALA CUP 2026")
        print(f"    Próxima Fecha : {state.next_match.date_label} ({state.next_match.time_label} hs)")
        print(f"    Estado        : {state.next_match.signup_window.message}")
        print(f"    Jugadores     : {len(state.players)} registrados en la base de datos")
        print(f"    Partidos      : {len(state.matches)} históricos")

        print("\n[+] Estadísticas Falopa Generales (Chalalytics):")
        print(f"    - Ediciones dominicales : {stats.editions}")
        print(f"    - Porros consumidos     : {stats.porros_smoked} porros")
        print(f"    - Materia verde quemada : {stats.grams_smoked} gramos")
        print(f"    - Tasa de Motalidad     : {stats.motality_rate}% (Lesiones/Ediciones)")

        print("\n[+] Top 3 Jugadores por Win Rate:")
        top = sorted(state.players, key=lambda x: (x.win_rate, x.overall), reverse=True)[:3]
        for i, p in enumerate(top, 1):
            print(f"    {i}. {p.display_name} -> {p.win_rate}% WR (Rating OVR: {p.overall})")

    except ChalaCupAPIError as e:
        print(f"[!] Error comunicando con Chala Cup: {e}")
    except Exception as e:
        print(f"[!] Error inesperado: {e}")

if __name__ == "__main__":
    run_demo()
