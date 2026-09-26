# Quantum Technology in MallHaul

## Implemented (running in this build)
1. Quantum-inspired optimisation for courier assignment (and multi-stop hub
   consolidation via 2-opt).
   - File: app/services/quantum_optimizer.py
   - Metropolis simulated annealing over a QUBO-style cost
     E(assignment) = total courier-to-pickup distance, geometric schedule
     T0=512 -> 0.5.
   - Called live by POST /api/ops/deliveries/{id}/assign and by the guided
     Demo page, which renders the optimizer report (energy trace).
   - Classical annealing is the accepted proxy for quantum annealing; the
     interface matches a D-Wave/QAOA solver, so production swap-in is a
     one-line change in delivery_service.py.

## Outlined (roadmap)
2. Post-quantum cryptography for wallet and session traffic.
   - Threat: "harvest now, decrypt later" against TLS protecting wallet
     top-ups and payment splits.
   - Plan: hybrid key exchange (X25519 + ML-KEM-768) at the load balancer,
     crypto-agility in the session token format for ML-DSA migration.
3. Quantum random number generation for QR code entropy.
   - Today: CSPRNG via the secrets module. Roadmap: QRNG appliance/API as
     the entropy source; the QR payload format does not change.

## Why this matters commercially
Courier distance is MallHaul's largest variable cost per order. Quantum
annealing solves exactly this class of combinatorial problem at fleet scale.