import os
from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.express as px

APP_TITLE = "Chigari InsightAI"
APP_TAGLINE = "Turn Data Into Clear Insights"


def load_dataset(file_obj):
    if file_obj is None:
        return None, "Please upload a CSV or Excel file to begin."

    path = str(file_obj)
    suffix = Path(path).suffix.lower()

    try:
        if suffix == ".csv":
            data = pd.read_csv(path)
        elif suffix in (".xlsx", ".xls"):
            data = pd.read_excel(path)
        else:
            return None, "Unsupported file type. Please upload CSV, XLSX, or XLS."
        if data.empty:
            return None, "The uploaded file has no rows."
        return data, f"Loaded {len(data):,} rows and {len(data.columns):,} columns."
    except Exception as exc:
        return None, f"Could not read the file: {exc}"


def analyze(file_obj):
    data, status = load_dataset(file_obj)
    if data is None:
        return (
            status,
            "No data quality report yet.",
            "No numerical summary yet.",
            pd.DataFrame(),
            gr.update(choices=[], value=None),
            gr.update(choices=[], value=None),
        )

    missing = data.isna().sum()
    missing_total = int(missing.sum())
    duplicate_rows = int(data.duplicated().sum())
    numeric = data.select_dtypes(include="number")

    missing_table = missing[missing > 0].rename("Missing cells").to_frame()
    missing_text = missing_table.to_string() if missing_total else "No missing values detected."

    quality = (
        "## Data quality\n"
        f"- **Rows:** {len(data):,}\n"
        f"- **Columns:** {len(data.columns):,}\n"
        f"- **Missing cells:** {missing_total:,}\n"
        f"- **Duplicate rows:** {duplicate_rows:,}\n"
        f"- **Numeric columns:** {len(numeric.columns)}\n\n"
        f"### Missing values by column\n```\n{missing_text}\n```"
    )

    summary = numeric.describe().round(2).to_string() if len(numeric.columns) else "No numeric columns were found."
    columns = list(data.columns)
    numeric_columns = list(numeric.columns)

    return (
        status,
        quality,
        f"```\n{summary}\n```",
        data.head(20),
        gr.update(choices=columns, value=columns[0] if columns else None),
        gr.update(choices=numeric_columns, value=numeric_columns[0] if numeric_columns else None),
    )


def make_chart(file_obj, x_col, y_col):
    data, status = load_dataset(file_obj)
    if data is None:
        return None, status
    if not x_col or not y_col:
        return None, "Choose an X column and a numeric Y column first."
    if x_col not in data.columns or y_col not in data.columns:
        return None, "Selected columns are not available in the uploaded dataset."

    try:
        if pd.api.types.is_numeric_dtype(data[x_col]):
            fig = px.scatter(data, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        else:
            grouped = data.groupby(x_col, dropna=False)[y_col].mean().reset_index()
            grouped = grouped.sort_values(y_col, ascending=False).head(30)
            fig = px.bar(grouped, x=x_col, y=y_col, title=f"Average {y_col} by {x_col}")
            fig.update_layout(xaxis_tickangle=-35)

        fig.update_layout(template="plotly_white")
        return fig, f"Chart created from {len(data):,} rows."
    except Exception as exc:
        return None, f"Could not create chart: {exc}"


with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as app:
    gr.Markdown(
        f"# {APP_TITLE}\n### {APP_TAGLINE}\n"
        "Upload a CSV or Excel dataset to inspect data quality, view numerical summaries, "
        "preview rows, and create a chart. Avoid uploading confidential or sensitive data."
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload your dataset (CSV or Excel)",
            file_types=[".csv", ".xlsx", ".xls"],
            type="filepath",
        )
        analyze_btn = gr.Button("Analyze My Data", variant="primary")

    status_box = gr.Markdown("Upload a dataset and select **Analyze My Data**.")

    with gr.Tab("Data Quality"):
        quality_box = gr.Markdown()

    with gr.Tab("Numerical Summary"):
        summary_box = gr.Markdown()

    with gr.Tab("Dataset Preview"):
        preview_box = gr.Dataframe(interactive=False, label="First 20 rows")

    with gr.Tab("Charts"):
        with gr.Row():
            x_dropdown = gr.Dropdown(label="X-axis / category column", choices=[])
            y_dropdown = gr.Dropdown(label="Numeric Y-axis column", choices=[])
        chart_btn = gr.Button("Create chart")
        chart_output = gr.Plot(label="Data visualization")
        chart_status = gr.Markdown()

    analyze_btn.click(
        analyze,
        inputs=[file_input],
        outputs=[
            status_box,
            quality_box,
            summary_box,
            preview_box,
            x_dropdown,
            y_dropdown,
        ],
    )

    chart_btn.click(
        make_chart,
        inputs=[file_input, x_dropdown, y_dropdown],
        outputs=[chart_output, chart_status],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.launch(server_name="0.0.0.0", server_port=port)
