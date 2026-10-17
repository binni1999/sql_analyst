from security.query_cost import QueryCostGuard


def test_query_plan_metrics_from_simple_plan():
    guard = QueryCostGuard.__new__(QueryCostGuard)

    plan = {
        "Node Type": "Limit",
        "Total Cost": 10.40,
        "Plan Rows": 5,
        "Plans": [
            {
                "Node Type": "Seq Scan",
                "Total Cost": 3.26,
                "Plan Rows": 126,
            },
            {
                "Node Type": "Hash Join",
                "Total Cost": 6.86,
                "Plan Rows": 80,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Total Cost": 1.80,
                        "Plan Rows": 80,
                    }
                ],
            },
        ],
    }

    metrics = {
        "total_cost": float(plan["Total Cost"]),
        "max_plan_rows": 0,
        "max_node_cost": 0.0,
        "sequential_scan_count": 0,
        "node_count": 0,
    }

    guard._walk_plan(plan, metrics)

    assert metrics["node_count"] == 4
    assert metrics["max_plan_rows"] == 126
    assert metrics["max_node_cost"] == 10.40
    assert metrics["sequential_scan_count"] == 2