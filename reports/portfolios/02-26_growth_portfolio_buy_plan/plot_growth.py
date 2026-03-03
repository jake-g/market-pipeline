# pylint: disable=duplicate-code
import os
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt


def create_detailed_decision_tree(output_path: str) -> None:
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  fig, ax = plt.subplots(figsize=(14, 8))
  ax.axis('off')

  nodes: Dict[str, Dict[str, Any]] = {
      "START": {
          "pos": (0.5, 0.95),
          "label": "$6,000 Cash\nMarket Down 3-5%",
          "color": "white"
      },
      "RSI_CHECK": {
          "pos": (0.5, 0.80),
          "label": "Is Asset RSI > 70\n& > 50% above 200MA?",
          "color": "lightyellow"
      },
      "OVEREXTENDED": {
          "pos": (0.2, 0.65),
          "label": "YES (Overextended)\ne.g. LRCX, COHR, AMAT",
          "color": "lightcoral"
      },
      "NORMALIZED": {
          "pos": (0.8, 0.65),
          "label": "NO (Normalized/Cool)\ne.g. NVDA, AMD, MPWR",
          "color": "lightgreen"
      },
      "ACTION_AVOID": {
          "pos": (0.2, 0.45),
          "label": "AVOID BUYING.\nLet mean-reversion\nplay out.",
          "color": "lightgray"
      },
      "SECTOR_CHECK": {
          "pos": (0.8, 0.45),
          "label": "Sector Profile?",
          "color": "lightyellow"
      },
      "SEMI_CORE": {
          "pos": (0.55, 0.25),
          "label": "Core Compute\n(NVDA, AMD)",
          "color": "lightblue"
      },
      "POWER_DATA": {
          "pos": (0.8, 0.25),
          "label": "Power/Datacenter\n(CEG, VST, MPWR)",
          "color": "lightblue"
      },
      "DEFENSIVE": {
          "pos": (1.05, 0.25),
          "label": "Defensive\n(PANW, LMT)",
          "color": "lightblue"
      },
      "BUY_SEMI": {
          "pos": (0.55, 0.05),
          "label": "BUY $2k NVDA\nBUY $1k AMD\n(Capture Discount)",
          "color": "lightgreen"
      },
      "BUY_POWER": {
          "pos": (0.8, 0.05),
          "label": "HOLD CASH.\nBuy if Semi bleed\ncontinues > 2 days.",
          "color": "lightgray"
      },
      "HOLD_DEF": {
          "pos": (1.05, 0.05),
          "label": "HOLD.\nDo not add\nrisk capital here.",
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
            size=9,
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.5",
                "facecolor": node_color,
                "edgecolor": "black",
                "alpha": 0.9
            })

  edges: List[Tuple[str, str]] = [("START", "RSI_CHECK"), ("RSI_CHECK", "OVEREXTENDED"),
           ("RSI_CHECK", "NORMALIZED"), ("OVEREXTENDED", "ACTION_AVOID"),
           ("NORMALIZED", "SECTOR_CHECK"), ("SECTOR_CHECK", "SEMI_CORE"),
           ("SECTOR_CHECK", "POWER_DATA"), ("SECTOR_CHECK", "DEFENSIVE"),
           ("SEMI_CORE", "BUY_SEMI"), ("POWER_DATA", "BUY_POWER"),
           ("DEFENSIVE", "HOLD_DEF")]

  for start, end in edges:
    start_x = float(nodes[start]["pos"][0])
    start_y = float(nodes[start]["pos"][1])
    end_x = float(nodes[end]["pos"][0])
    end_y = float(nodes[end]["pos"][1])

    edge_label = ""
    if start == "RSI_CHECK" and end == "OVEREXTENDED":
      edge_label = "YES"
    if start == "RSI_CHECK" and end == "NORMALIZED":
      edge_label = "NO"

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

    if edge_label:
      mid_x = (start_x + end_x) / 2.0
      mid_y = (start_y + end_y) / 2.0
      ax.text(mid_x,
              mid_y,
              edge_label,
              fontsize=8,
              ha='center',
              va='center',
              backgroundcolor='white')

  plt.title("Portfolio Allocation Logic (2/26)",
            fontsize=16,
            fontweight='bold',
            y=1.0)
  plt.xlim(0, 1.25)
  plt.ylim(-0.1, 1.1)

  plt.savefig(output_path, bbox_inches='tight', dpi=150)
  plt.close()


if __name__ == "__main__":
  create_detailed_decision_tree(
      "reports/02-26_growth_portfolio_buy_plan/plots/decision_tree.png")
