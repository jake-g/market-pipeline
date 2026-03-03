# pylint: disable=duplicate-code
import os
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt


def create_roth_decision_tree(output_path: str) -> None:
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  fig, ax = plt.subplots(figsize=(10, 6))
  ax.axis('off')

  nodes: Dict[str, Dict[str, Any]] = {
      "CASH": {
          "pos": (0.5, 0.9),
          "label": "$800 Cash\n(Roth IRA - Aggressive)",
          "color": "white"
      },
      "NVDA_STATUS": {
          "pos": (0.5, 0.7),
          "label": "Recent 5 NVDA Position\nUnderwater (-5%)",
          "color": "lightyellow"
      },
      "ACTION_AVERAGE": {
          "pos": (0.2, 0.4),
          "label": "DEPLOY NOW:\nBuy 4-5 NVDA (~$800)\nAverage Down Entry",
          "color": "lightgreen"
      },
      "ACTION_DIVERSIFY": {
          "pos": (0.8, 0.4),
          "label": "DIVERSIFY DIPS:\nBuy TSM or AMZN",
          "color": "lightblue"
      },
      "OUTCOME_AVERAGE": {
          "pos": (0.2, 0.1),
          "label": "Tax-Free Compounding\non Rebound",
          "color": "gold"
      },
      "OUTCOME_DIVERSIFY": {
          "pos": (0.8, 0.1),
          "label": "Reduces NVDA Beta\nbut lowers max yield",
          "color": "lightgray"
      }
  }

  for k, v in nodes.items():
    pos_x = float(v["pos"][0])
    pos_y = float(v["pos"][1])
    node_label = str(v["label"])
    node_color = str(v["color"])
    ax.text(pos_x,
            pos_y,
            node_label,
            size=10,
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.5",
                "facecolor": node_color,
                "edgecolor": "black",
                "alpha": 0.9
            })

  edges: List[Tuple[str, str]] = [("CASH", "NVDA_STATUS"), ("NVDA_STATUS", "ACTION_AVERAGE"),
           ("NVDA_STATUS", "ACTION_DIVERSIFY"),
           ("ACTION_AVERAGE", "OUTCOME_AVERAGE"),
           ("ACTION_DIVERSIFY", "OUTCOME_DIVERSIFY")]

  for start, end in edges:
    start_x = float(nodes[start]["pos"][0])
    start_y = float(nodes[start]["pos"][1])
    end_x = float(nodes[end]["pos"][0])
    end_y = float(nodes[end]["pos"][1])

    ax.annotate("",
                xy=(end_x, end_y + 0.06),
                xycoords='data',
                xytext=(start_x, start_y - 0.06),
                textcoords='data',
                arrowprops={
                    "arrowstyle": "->",
                    "color": "black",
                    "lw": 1.5,
                    "shrinkA": 5,
                    "shrinkB": 5
                })

  plt.title("Roth IRA Aggressive Deployment Plan ($800)",
            fontsize=14,
            fontweight='bold',
            y=1.0)
  plt.xlim(0, 1)
  plt.ylim(-0.1, 1.1)

  plt.savefig(output_path, bbox_inches='tight', dpi=150)
  plt.close()


if __name__ == "__main__":
  create_roth_decision_tree(
      "reports/02-26_roth_ira_plan/plots/decision_tree.png")
