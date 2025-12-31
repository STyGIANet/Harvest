import json
import sys
from synthesis import DPScheduler

def main():
    if len(sys.argv) != 9:
        raise SystemExit(
            "usage: python generate-schedule.py collective.json d c alpha_r out.json"
        )

    in_file = sys.argv[1]
    d = int(sys.argv[2])
    c = float(sys.argv[3]) # c in the command line arguments must be specified as Gbps
    beta = 1/c
    alpha = float(sys.argv[4]) # setup delay (nanoseconds)
    delta = float(sys.argv[5]) # propagation delay (nanoseconds)
    alpha_r = float(sys.argv[6]) # reconfiguration delay (nanoseconds)
    logging = int(sys.argv[7])
    out_file = sys.argv[8]

    with open(in_file) as f:
        doc = json.load(f)

    n = doc["n"]
    # Note: Size is converted to bits here
    steps = [[(u, v, m * 8) for (u, v, m) in s["demand"]] for s in doc["steps"]]

    scheduler = DPScheduler(
        steps=steps,
        num_nodes=n,
        d=d,
        c=c,
        beta=beta,
        alpha=alpha,
        delta=delta,
        alpha_r=alpha_r,
        logging = logging,
    )

    cost, schedule = scheduler.synthesize()
    # print(schedule, len(steps))
    stepTopos = scheduler.expandSchedulePerStep(schedule, len(steps))

    # The output gives the matchings in each step, 
    # and may also give multiple edges between same nodes for degree>1 scenarios
    out = {
        "total_cost": cost,
        "steps": [
            {
                "step": i + 1,
                "topology": [[u, v, k] for (u, v), k in topo.items()],
            }
            for i, topo in enumerate(stepTopos)
        ],
    }


    with open(out_file, "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()