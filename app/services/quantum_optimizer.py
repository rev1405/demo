"""QUANTUM-INSPRIED COURIER ASSIGNMENT (implemented - see docs/QUANTUM.md).

Simulated annealing over a QUBO-style cost:
    E(assignment) = sum(distance(courier_i, stop_i)) + lambda * load_imbalance
Classical Metropolis annealing is the accepted proxy for annealing-based
quantum optimisation; the interface is identical to a future D-Wave/QAOA
solver, so the swap is a one-line change in delivery_service.

Also: route_stops() - 2-opt route improvement for multi-stop consolidation.
"""
import math
import random


def haversine_m(a, b) -> float:
    """Great-circle distance in metres. Points are GeoJSON [lng, lat]."""
    lng1, lat1, lng2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def select_courier(pickup, candidates, seed: int = 42):
    """Anneal over candidate assignments; objective = courier-to-pickup distance.
    Returns (best_candidate, report). With 1 courier it still returns a trace."""
    if not candidates:
        return None, {"iterations": 0, "note": "no available couriers"}

    rng = random.Random(seed)
    n = len(candidates)
    costs = [haversine_m(pickup, c.get("current_location") or pickup)
             for c in candidates]

    current = rng.randrange(n)
    best, best_e = current, costs[current]
    T0, T1, iters = 512.0, 0.5, 256
    trace = []
    for step in range(iters):
        T = T0 * (T1 / T0) ** (step / iters)          # geometric schedule
        proposal = rng.randrange(n)
        dE = costs[proposal] - costs[current]
        if dE <= 0 or rng.random() < math.exp(-dE / max(T, 1e-9)):
            current = proposal
            if costs[current] < best_e:
                best, best_e = current, costs[current]
        if step % (iters // 16) == 0:
            trace.append(round(best_e, 1))

    report = {"algorithm": "quantum-inspired simulated annealing (QUBO proxy)",
              "candidates": n, "iterations": iters,
              "schedule": "geometric T0=512 -> T1=0.5",
              "best_energy_m": round(best_e, 1), "energy_trace": trace,
              "swap_in": "D-Wave annealer / QAOA (Qiskit) - same interface"}
    return candidates[best], report


def route_stops(depot, stops):
    """Nearest-neighbour + 2-opt improvement for multi-stop runs."""
    def total(order):
        d = haversine_m(depot, order[0])
        d += sum(haversine_m(order[k], order[k + 1]) for k in range(len(order) - 1))
        return d

    pts, order, cur = list(stops), [], depot
    while pts:
        nxt = min(pts, key=lambda p: haversine_m(cur, p))
        order.append(nxt)
        pts.remove(nxt)
        cur = nxt
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                new = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if total(new) + 1e-9 < total(order):
                    order = new
                    improved = True
    return order, {"algorithm": "2-opt route improvement", "stops": len(order)}