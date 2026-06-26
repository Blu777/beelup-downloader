import argparse
import sys
from getpass import getpass
from .client import ChalaCupClient, ChalaCupAPIError

def main():
    parser = argparse.ArgumentParser(description="CLI oficial para CHALA CUP CLUB")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # Comando status
    subparsers.add_parser("status", help="Muestra el estado general de la fecha dominical")

    # Comando leaderboard
    subparsers.add_parser("leaderboard", help="Muestra el ranking de jugadores por WR y Overall")

    # Comando login
    login_p = subparsers.add_parser("login", help="Inicia sesión y guarda el token local")
    login_p.add_argument("--email", "-e", type=str, help="Correo electrónico")

    # Comando signup
    subparsers.add_parser("signup", help="Inscríbete al próximo partido")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = ChalaCupClient()

    try:
        if args.command == "status":
            state = client.get_bootstrap()
            nm = state.next_match
            stats = client.get_general_stats()

            print("\n=== [ CHALA CUP: PARTE DOMINICAL ] ===")
            print(f"[*] Próximo Partido : {nm.date_label} a las {nm.time_label}")
            print(f"[*] Ventana         : {'ABIERTA' if nm.signup_window.is_open else 'CERRADA'} -> {nm.signup_window.message}")
            print(f"[*] Anotados        : {nm.signed_count} / {nm.max_signups}")
            print(f"[*] Equipos listos  : {'SÍ' if nm.teams_ready else 'NO'}")
            print("\n--- [ CHALALYTICS ] ---")
            print(f"[*] Ediciones jugadas   : {stats.editions}")
            print(f"[*] Porros quemados     : {stats.porros_smoked} ({stats.grams_smoked} g)")
            print(f"[*] Tasa de motalidad   : {stats.motality_rate}%")
            print("======================================\n")

        elif args.command == "leaderboard":
            state = client.get_bootstrap()
            players = sorted(state.players, key=lambda x: (x.win_rate, x.overall), reverse=True)

            print("\n=== [ TOP PORREROS & JUGADORES ] ===")
            print(f"{'#':<3} {'Nombre':<28} {'Posición':<16} {'WR%':<8} {'OVR':<6}")
            print("-" * 65)
            for i, p in enumerate(players[:15], 1):
                pos = p.primary_position or p.position or "INV"
                print(f"{i:<3} {p.display_name:<28} {pos:<16} {p.win_rate:<8.1f} {p.overall:<6}")
            print("=====================================\n")

        elif args.command == "login":
            email = args.email
            if not email:
                email = input("Mail de Chala Cup: ").strip()
            password = getpass("Password: ")
            print("[*] Conectando con el growshop digital...")
            token = client.login(email, password)
            print(f"[+] Login exitoso! Token guardado en .chala_token")

        elif args.command == "signup":
            state = client.get_bootstrap()
            print(f"[*] Anotándote a {state.next_match.date_label}...")
            res = client.signup_for_match(state.next_match.id)
            print(f"[+] {res.get('message', 'Anotado correctamente!')}")

    except ChalaCupAPIError as e:
        print(f"\n[!] Error de la API: {e}\n", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\n[!] Error inesperado: {e}\n", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()
