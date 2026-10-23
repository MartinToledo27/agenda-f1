import json, urllib.request
from datetime import datetime, timezone

J = "https://api.jolpi.ca/ergast/f1/current"
SES = {"FirstPractice": "FP1", "SecondPractice": "FP2", "ThirdPractice": "FP3",
       "SprintQualifying": "SQ", "Sprint": "SPR", "Qualifying": "Q"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["MRData"]


def cargar(nombre, defecto):
    try:
        return json.load(open(nombre, encoding="utf-8"))
    except Exception:
        return defecto


viejo = cargar("data.json", {})
trans = cargar("transmision.json", {})  # "ronda-SESION": ["desde", "hasta"] en hora argentina
nuevo = dict(viejo)


def intentar(clave, fn):
    try:
        nuevo[clave] = fn()
    except Exception as ex:
        print("Fallo", clave, ex)


def calendario():
    out = []
    for r in get(J + ".json")["RaceTable"]["Races"]:
        ses = [(k, r[n]) for n, k in SES.items() if n in r] + [("R", r)]
        ses = sorted(({"k": k, "t": s["date"] + "T" + s["time"]} for k, s in ses), key=lambda s: s["t"])
        for s in ses:
            d = trans.get(f"{r['round']}-{s['k']}")
            if d:
                s["d"] = d
        c = r["Circuit"]
        out.append({"ronda": int(r["round"]), "nombre": r["raceName"], "circuito": c["circuitName"],
                    "ciudad": c["Location"]["locality"], "pais": c["Location"]["country"], "sesiones": ses})
    return out


def pilotos():
    t = get(J + "/driverStandings.json")["StandingsTable"]["StandingsLists"][0]
    return [{"pos": int(x["position"]), "cod": x["Driver"]["code"], "nombre": x["Driver"]["givenName"] + " " + x["Driver"]["familyName"],
             "num": x["Driver"].get("permanentNumber"), "equipo": x["Constructors"][-1]["name"],
             "equipoId": x["Constructors"][-1]["constructorId"], "pts": float(x["points"])} for x in t["DriverStandings"]]


def constructores():
    t = get(J + "/constructorStandings.json")["StandingsTable"]["StandingsLists"][0]
    return [{"pos": int(x["position"]), "id": x["Constructor"]["constructorId"], "nombre": x["Constructor"]["name"],
             "pts": float(x["points"])} for x in t["ConstructorStandings"]]


def ultimo():
    r = get(J + "/last/results.json")["RaceTable"]["Races"][0]
    return {"ronda": int(r["round"]), "nombre": r["raceName"], "resultados": [
        {"pos": x["positionText"], "cod": x["Driver"]["code"], "equipoId": x["Constructor"]["constructorId"],
         "grid": x["grid"], "estado": x["status"], "tiempo": (x.get("Time") or {}).get("time", ""), "pts": x["points"]}
        for x in r["Results"]]}


intentar("carreras", calendario)
intentar("pilotos", pilotos)
intentar("constructores", constructores)
intentar("ultimo", ultimo)

base = {k: v for k, v in viejo.items() if k != "actualizado"}
cmp = {k: v for k, v in nuevo.items() if k != "actualizado"}
if cmp == base:
    print("Sin cambios")
else:
    nuevo["actualizado"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(nuevo, f, ensure_ascii=False, separators=(",", ":"))
    print("data.json actualizado:", len(nuevo.get("carreras", [])), "carreras")
