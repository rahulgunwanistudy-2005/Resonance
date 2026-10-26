"""Build the technical report from source references and actual evaluator JSON."""

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fontTools.ttLib import TTFont as ConvertFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from scripts.check_no_hardcoded_metrics import TOKEN, check_text, resolve


def main() -> None:
    output = Path("docs/report")
    output.mkdir(exist_ok=True)
    temporary = Path("outputs/report-assets")
    temporary.mkdir(parents=True, exist_ok=True)
    for weight in (400, 600):
        source = Path(
            f"web/node_modules/@fontsource/overpass/files/overpass-latin-{weight}-normal.woff"
        )
        font = ConvertFont(source)
        font.flavor = None
        font.save(temporary / f"overpass-{weight}.ttf")
        pdfmetrics.registerFont(
            TTFont(
                "Overpass" if weight == 400 else "OverpassBold",
                str(temporary / f"overpass-{weight}.ttf"),
            )
        )
    raw = Path("docs/report/report.md").read_text()
    failures = check_text(raw)
    if failures:
        raise ValueError("\n".join(failures))
    rendered = TOKEN.sub(
        lambda match: str(resolve(match[0]))
        if isinstance(resolve(match[0]), int)
        else f"{resolve(match[0]):.4g}",
        raw,
    )
    (temporary / "technical-report.md").write_text(rendered)
    evaluation = json.loads(Path("eval/results/synthetic.json").read_text())
    figure, axes = plt.subplots(1, 2, figsize=(7, 3.0), layout="constrained")
    for name, color, label in [
        ("extract_phase_correlation", "#8A3B17", "Phase correlation"),
        ("extract_riesz", "#285C58", "Riesz local phase"),
    ]:
        rows = [
            row
            for row in evaluation["experiments"]
            if row["method"] == name and row.get("eligible_for_target")
        ]
        axes[0].scatter(
            range(len(rows)),
            [row["frequency_error_percent"] for row in rows],
            s=12,
            color=color,
            label=label,
        )
        axes[1].scatter(
            range(len(rows)),
            [row["amplitude_error_percent"] for row in rows],
            s=12,
            color=color,
            label=label,
        )
    axes[0].axhline(
        evaluation["targets"]["frequency_error_percent"],
        color="#795500",
        linestyle="--",
        linewidth=1,
    )
    axes[1].axhline(
        evaluation["targets"]["amplitude_error_percent"],
        color="#795500",
        linestyle="--",
        linewidth=1,
    )
    for axis, label in zip(
        axes, ["Frequency error (%)", "Amplitude error (%)"], strict=True
    ):
        axis.set_ylabel(label)
        axis.set_xlabel("Eligible synthetic input")
        axis.tick_params(labelsize=8)
    axes[0].legend(fontsize=7, loc="upper right")
    figure.savefig(temporary / "evaluation.png", dpi=180)
    plt.close(figure)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "BodyCustom",
            fontName="Overpass",
            fontSize=9.5,
            leading=13,
            spaceAfter=7,
            textColor=colors.HexColor("#1F2B33"),
        )
    )
    styles.add(
        ParagraphStyle(
            "TitleCustom",
            fontName="OverpassBold",
            fontSize=25,
            leading=29,
            spaceAfter=16,
            textColor=colors.HexColor("#1F2B33"),
        )
    )
    styles.add(
        ParagraphStyle(
            "HeadingCustom",
            fontName="OverpassBold",
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle("CellCustom", fontName="Overpass", fontSize=9, leading=12)
    )
    story = []
    lines = rendered.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(html.escape(line[2:]), styles["TitleCustom"]))
            index += 1
            continue
        if line.startswith("## "):
            if line == "## References":
                story.append(PageBreak())
            story.append(Paragraph(html.escape(line[3:]), styles["HeadingCustom"]))
            index += 1
            continue
        if line.startswith("- "):
            story.append(
                Paragraph(html.escape(line[2:]), styles["CellCustom"], bulletText="-")
            )
            story.append(Spacer(1, 5))
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [
                    value.strip()
                    for value in lines[index].strip().strip("|").split("|")
                ]
                if not all(set(value) <= set("-: ") for value in cells):
                    rows.append(
                        [
                            Paragraph(html.escape(value), styles["CellCustom"])
                            for value in cells
                        ]
                    )
                index += 1
            table = Table(
                rows, colWidths=[125 * mm, 40 * mm], repeatRows=1, hAlign="LEFT"
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D5D7D3")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        (
                            "LINEBELOW",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.HexColor("#B7C0B9"),
                        ),
                    ]
                )
            )
            story.extend(
                [
                    table,
                    Spacer(1, 10),
                    Image(
                        str(temporary / "evaluation.png"),
                        width=165 * mm,
                        height=71 * mm,
                    ),
                ]
            )
            continue
        paragraph = []
        while (
            index < len(lines)
            and lines[index].strip()
            and not lines[index].startswith(("#", "|"))
        ):
            paragraph.append(lines[index].strip())
            index += 1
        story.append(Paragraph(html.escape(" ".join(paragraph)), styles["BodyCustom"]))

    def footer(canvas, document):
        canvas.setFont("Overpass", 8)
        canvas.setFillColor(colors.HexColor("#485A60"))
        canvas.drawString(
            22 * mm,
            14 * mm,
            "Resonance | Local evidence and explicit validation limits",
        )
        canvas.drawRightString(188 * mm, 14 * mm, str(document.page))

    document = SimpleDocTemplate(
        str(output / "resonance-technical-report.pdf"),
        pagesize=(210 * mm, 297 * mm),
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=24 * mm,
        title="Resonance technical report",
        author="Rahul",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print("Built docs/report/resonance-technical-report.pdf from measured JSON sources")


if __name__ == "__main__":
    main()
