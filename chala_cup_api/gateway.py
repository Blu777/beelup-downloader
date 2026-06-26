"""
Microservicio Gateway Flask

Conecta la API de Chala Cup Club con el sistema local de Beelup Downloader.
Permite enlazar partidos descargados con las fechas del torneo.
"""

from flask import Flask, jsonify, request
from .client import ChalaCupClient, ChalaCupAPIError

app = Flask(__name__)
client = ChalaCupClient()

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "chala-cup-gateway"})

@app.route("/api/v1/tournament/overview", methods=["GET"])
def tournament_overview():
    try:
        data = client.get_bootstrap()
        stats = client.get_general_stats()
        return jsonify({
            "next_match": {
                "date_label": data.next_match.date_label,
                "time_label": data.next_match.time_label,
                "signed_count": data.next_match.signed_count,
                "max_signups": data.next_match.max_signups,
                "is_open": data.next_match.signup_window.is_open,
                "message": data.next_match.signup_window.message
            },
            "analytics": {
                "editions": stats.editions,
                "porros_smoked": stats.porros_smoked,
                "grams_smoked": stats.grams_smoked,
                "motality_rate": stats.motality_rate
            },
            "players_count": len(data.players)
        })
    except ChalaCupAPIError as e:
        return jsonify({"error": str(e)}), 502

@app.route("/api/v1/integration/link-beelup", methods=["POST"])
def link_beelup_match():
    """
    Endpoint para enlazar un ID de partido de Beelup con una fecha dominical de Chala Cup.
    Payload esperado: {"beelup_match_id": "26745803", "chala_match_id": "domingo-20260628"}
    """
    payload = request.get_json() or {}
    beelup_id = payload.get("beelup_match_id")
    chala_id = payload.get("chala_match_id")

    if not beelup_id or not chala_id:
        return jsonify({"error": "Faltan parámetros beelup_match_id o chala_match_id"}), 400

    # Aquí se puede conectar con downloader_core.py de Beelup Downloader
    return jsonify({
        "status": "linked",
        "message": f"Partido Beelup {beelup_id} enlazado exitosamente con fecha Chala Cup {chala_id}"
    })

if __name__ == "__main__":
    app.run(port=5050, debug=True)
