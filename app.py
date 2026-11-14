"""Streamlit front end for the preliminary circular RCC bunker calculator.

This app is a deployment-oriented adaptation of the notebook-export starter.
Its calculations are indicative only and are not a substitute for a complete,
independently checked structural design.
"""

from __future__ import annotations

from io import BytesIO
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Circular RCC Bunker | Design Explorer",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1440px;}
      .hero {padding: 1.35rem 1.6rem; border-radius: 16px;
             background: linear-gradient(120deg, #102a43, #176b87); color: white;
             margin-bottom: 1rem;}
      .hero h1 {margin: 0 0 .35rem 0; font-size: 2rem;}
      .hero p {margin: 0; opacity: .88;}
      div[data-testid="stMetric"] {background: #f4f8fb; border: 1px solid #e4edf3;
             padding: 14px 16px; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>Circular RCC Bunker</h1>'
    '<p>Preliminary geometry, stored-material pressure, reinforcement estimate, and quantity schedule</p></div>',
    unsafe_allow_html=True,
)
st.warning(
    "Engineering prototype — outputs are preliminary estimates, not a code-compliant or "
    "construction-ready design. Verify load cases, granular-flow assumptions, all limit states, "
    "detailing, and applicable IS editions with a qualified structural engineer before use.",
    icon="⚠️",
)

with st.sidebar:
    st.header("Project inputs")
    with st.form("design_inputs"):
        project_name = st.text_input("Project name", "Circular RCC Bunker Project")
        location = st.text_input("Location", "India")
        designer = st.text_input("Designer", "")

        st.subheader("Geometry")
        diameter = st.number_input("Internal diameter (m)", min_value=0.1, value=10.0, step=0.5)
        cylinder_height = st.number_input("Cylindrical height (m)", min_value=0.1, value=15.0, step=0.5)
        hopper_height = st.number_input("Hopper height (m)", min_value=0.1, value=4.0, step=0.25)
        outlet_diameter = st.number_input("Outlet diameter (m)", min_value=0.05, value=1.0, step=0.1)
        wall_thickness_mm = st.number_input("Wall thickness (mm)", min_value=50.0, value=250.0, step=10.0)
        hopper_thickness_mm = st.number_input("Hopper thickness (mm)", min_value=50.0, value=200.0, step=10.0)
        ring_beam_width_mm = st.number_input("Ring beam width (mm)", min_value=100.0, value=500.0, step=25.0)
        ring_beam_depth_mm = st.number_input("Ring beam depth (mm)", min_value=100.0, value=700.0, step=25.0)
        column_width_mm = st.number_input("Column width (mm)", min_value=100.0, value=500.0, step=25.0)
        column_depth_mm = st.number_input("Column depth (mm)", min_value=100.0, value=500.0, step=25.0)
        column_height = st.number_input("Column height (m)", min_value=0.1, value=5.0, step=0.25)
        number_of_columns = st.number_input("Number of columns", min_value=1, max_value=64, value=8, step=1)

        st.subheader("Materials and stored product")
        concrete_grade = st.selectbox("Concrete grade", ["M20", "M25", "M30", "M35", "M40"], index=2)
        steel_grade = st.selectbox("Reinforcement steel", ["Fe415", "Fe500", "Fe500D"], index=1)
        concrete_cover_mm = st.number_input("Nominal cover (mm)", min_value=15.0, value=40.0, step=5.0)
        concrete_density = st.number_input("RCC density (kN/m³)", min_value=1.0, value=25.0, step=0.5)
        stored_density = st.number_input("Stored material bulk density (kN/m³)", min_value=0.1, value=16.0, step=0.5)
        friction_coefficient = st.number_input("Wall friction coefficient μ", min_value=0.01, max_value=1.0, value=0.30, step=0.01)
        lateral_coefficient = st.number_input("Lateral pressure coefficient K", min_value=0.01, max_value=2.0, value=0.40, step=0.01)

        st.subheader("Additional loads (recorded only)")
        live_load = st.number_input("Live load (kN/m²)", min_value=0.0, value=5.0, step=0.5)
        wind_pressure = st.number_input("Wind pressure (kN/m²)", min_value=0.0, value=1.0, step=0.1)
        seismic_coefficient = st.number_input("Seismic coefficient", min_value=0.0, max_value=1.0, value=0.10, step=0.01)
        equipment_load = st.number_input("Equipment load (kN)", min_value=0.0, value=20.0, step=1.0)

        st.subheader("Reinforcement schedule assumptions")
        wall_hoop_bar = st.number_input("Wall hoop bar diameter (mm)", min_value=6, max_value=40, value=12, step=1)
        wall_hoop_spacing = st.number_input("Wall hoop spacing (mm)", min_value=25, max_value=500, value=150, step=5)
        wall_vertical_bar = st.number_input("Wall vertical bar diameter (mm)", min_value=6, max_value=40, value=16, step=1)
        wall_vertical_spacing = st.number_input("Wall vertical spacing (mm)", min_value=25, max_value=500, value=150, step=5)
        hopper_bar = st.number_input("Hopper bar diameter (mm)", min_value=6, max_value=40, value=16, step=1)
        hopper_spacing = st.number_input("Hopper bar spacing (mm)", min_value=25, max_value=500, value=150, step=5)
        lap_allowance = st.number_input("Lap / anchorage allowance per bar (m)", min_value=0.0, value=0.60, step=0.05)

        submitted = st.form_submit_button("Update calculations", type="primary", use_container_width=True)

# Forms initialize values on the first run; calculate on every Streamlit rerun thereafter.
# The submit flag is intentionally not required so the app always has a usable initial view.
_ = submitted

if outlet_diameter >= diameter:
    st.error("Outlet diameter must be smaller than the bunker internal diameter.")
    st.stop()
if concrete_cover_mm >= min(wall_thickness_mm, hopper_thickness_mm):
    st.error("Concrete cover must be less than both wall and hopper thickness.")
    st.stop()

fck = {"M20": 20.0, "M25": 25.0, "M30": 30.0, "M35": 35.0, "M40": 40.0}[concrete_grade]
fy = {"Fe415": 415.0, "Fe500": 500.0, "Fe500D": 500.0}[steel_grade]

radius = diameter / 2
outlet_radius = outlet_diameter / 2
wall_thickness = wall_thickness_mm / 1000
hopper_thickness = hopper_thickness_mm / 1000
beam_width = ring_beam_width_mm / 1000
beam_depth = ring_beam_depth_mm / 1000
column_width = column_width_mm / 1000
column_depth = column_depth_mm / 1000

cylinder_volume = math.pi * radius**2 * cylinder_height
hopper_volume = (
    math.pi * hopper_height / 3
    * (radius**2 + radius * outlet_radius + outlet_radius**2)
)
storage_volume = cylinder_volume + hopper_volume
stored_weight = storage_volume * stored_density
stored_mass_tonnes = stored_weight / 9.80665
hopper_slant = math.hypot(hopper_height, radius - outlet_radius)
hopper_angle_deg = math.degrees(math.atan2(hopper_height, radius - outlet_radius))
hopper_surface_area = math.pi * (radius + outlet_radius) * hopper_slant

outer_diameter = diameter + 2 * wall_thickness
wall_concrete_volume = math.pi / 4 * (outer_diameter**2 - diameter**2) * cylinder_height
hopper_concrete_volume = hopper_surface_area * hopper_thickness
beam_mean_radius = radius + wall_thickness + beam_width / 2
beam_concrete_volume = 2 * math.pi * beam_mean_radius * beam_width * beam_depth
column_concrete_volume = number_of_columns * column_width * column_depth * column_height
total_concrete_volume = wall_concrete_volume + hopper_concrete_volume + beam_concrete_volume + column_concrete_volume
concrete_self_weight = total_concrete_volume * concrete_density

# Janssen-type cylindrical-wall pressure profile; filling and emptying use the same
# material parameters here because separate condition parameters are not supplied.
hydraulic_radius = diameter / 4
characteristic_depth = hydraulic_radius / (friction_coefficient * lateral_coefficient)
depth = np.linspace(0.0, cylinder_height, 101)
pressure_factor = 1.0 - np.exp(-depth / characteristic_depth)
vertical_pressure = stored_density * hydraulic_radius / (friction_coefficient * lateral_coefficient) * pressure_factor
horizontal_pressure = stored_density * hydraulic_radius / friction_coefficient * pressure_factor
wall_friction_pressure = stored_density * hydraulic_radius * pressure_factor
hoop_tension = horizontal_pressure * diameter / 2
hoop_stress = hoop_tension / wall_thickness_mm

pressure_df = pd.DataFrame({
    "Depth from surface (m)": depth,
    "Vertical pressure (kN/m²)": vertical_pressure,
    "Horizontal pressure (kN/m²)": horizontal_pressure,
    "Wall friction pressure (kN/m²)": wall_friction_pressure,
    "Hoop tension (kN/m)": hoop_tension,
})

# Preliminary steel estimate only: assumed minimum ratio and equal distribution to two faces.
minimum_steel_ratio = 0.0012
minimum_steel = minimum_steel_ratio * 1000 * wall_thickness_mm
required_steel = hoop_tension * 1000 / (0.87 * fy)
design_steel = np.maximum(required_steel, minimum_steel)
bar_area = math.pi * wall_hoop_bar**2 / 4
spacing_from_demand = 1000 * bar_area / (design_steel / 2)
provided_hoop_spacing = min(float(wall_hoop_spacing), 300.0)
provided_hoop_steel = 2 * bar_area * 1000 / provided_hoop_spacing
reinforcement_df = pd.DataFrame({
    "Depth (m)": depth,
    "Hoop tension (kN/m)": hoop_tension,
    "Required steel (mm²/m)": required_steel,
    "Assumed minimum steel (mm²/m)": minimum_steel,
    "Design steel (mm²/m)": design_steel,
    "Demand-based spacing (mm)": spacing_from_demand,
    "Provided steel at selected spacing (mm²/m)": provided_hoop_steel,
})

# Summary tables
geometry_df = pd.DataFrame([
    ("Internal diameter", diameter, "m"),
    ("Outer diameter", outer_diameter, "m"),
    ("Cylindrical wall height", cylinder_height, "m"),
    ("Hopper height", hopper_height, "m"),
    ("Calculated hopper angle from horizontal", hopper_angle_deg, "degrees"),
    ("Hopper sloping length", hopper_slant, "m"),
    ("Cylindrical storage volume", cylinder_volume, "m³"),
    ("Hopper storage volume", hopper_volume, "m³"),
    ("Total storage volume", storage_volume, "m³"),
    ("Stored material weight", stored_weight, "kN"),
    ("Stored material mass", stored_mass_tonnes, "tonnes"),
    ("Estimated total RCC volume", total_concrete_volume, "m³"),
    ("Estimated RCC self-weight", concrete_self_weight, "kN"),
], columns=["Parameter", "Value", "Unit"])

st.caption(f"Project: **{project_name or 'Untitled'}** · {location or 'Location not set'} · Designer: {designer or 'Not specified'}")

metric_cols = st.columns(4)
metric_cols[0].metric("Storage volume", f"{storage_volume:,.1f} m³")
metric_cols[1].metric("Stored mass", f"{stored_mass_tonnes:,.1f} t")
metric_cols[2].metric("Max. horizontal pressure", f"{horizontal_pressure[-1]:,.1f} kN/m²")
metric_cols[3].metric("Max. hoop tension", f"{hoop_tension[-1]:,.1f} kN/m")

tab_summary, tab_loads, tab_structure, tab_model, tab_bbs = st.tabs([
    "Overview", "Pressure analysis", "Preliminary wall estimate", "Drawings & 3D", "Quantity schedule"
])

with tab_summary:
    st.subheader("Geometry and quantity summary")
    st.dataframe(geometry_df.style.format({"Value": "{:,.3f}"}), use_container_width=True, hide_index=True)
    st.info(
        f"Entered concrete: {concrete_grade} (fck = {fck:.0f} MPa) · "
        f"Steel: {steel_grade} (fy = {fy:.0f} MPa). Live, wind, seismic, and equipment inputs are recorded but are not combined into the pressure model."
    )
    with st.expander("Calculation assumptions and scope"):
        st.markdown(
            "- Storage volume is a cylinder plus a circular frustum.\n"
            "- Cylindrical stored-material pressures use the starter's Janssen-type expression and one common parameter set.\n"
            "- Hopper pressure, structural load combinations, wall bending, crack width, shear, seismic response, foundation, and code detailing are not designed here.\n"
            "- Concrete and reinforcement quantities are geometric/preliminary estimates; openings, laps, wastage, and detailed bar shapes are not fully represented."
        )

with tab_loads:
    st.subheader("Cylindrical-wall pressure distribution")
    pressure_fig = go.Figure()
    for column, label, color in [
        ("Vertical pressure (kN/m²)", "Vertical", "#0f766e"),
        ("Horizontal pressure (kN/m²)", "Horizontal", "#2563eb"),
        ("Wall friction pressure (kN/m²)", "Wall friction", "#ea580c"),
    ]:
        pressure_fig.add_trace(go.Scatter(
            x=pressure_df[column], y=pressure_df["Depth from surface (m)"],
            mode="lines", name=label, line={"width": 3, "color": color}
        ))
    pressure_fig.update_layout(
        xaxis_title="Pressure (kN/m²)", yaxis_title="Depth from surface (m)",
        height=470, margin={"l": 20, "r": 20, "t": 20, "b": 20},
        legend={"orientation": "h", "y": 1.1},
    )
    pressure_fig.update_yaxes(autorange="reversed")
    st.plotly_chart(pressure_fig, use_container_width=True)
    st.caption(f"Hydraulic radius = {hydraulic_radius:.3f} m · Characteristic depth = {characteristic_depth:.3f} m. Filling and emptying are identical in this prototype because separate inputs are not implemented.")
    st.dataframe(pressure_df.round(3), use_container_width=True, hide_index=True)
    st.download_button(
        "Download pressure profile (CSV)", pressure_df.to_csv(index=False).encode("utf-8"),
        file_name="bunker_pressure_profile.csv", mime="text/csv"
    )

with tab_structure:
    st.subheader("Indicative cylindrical-wall hoop reinforcement")
    st.caption("Screening estimate only. Uses a fixed assumed minimum ratio and divides hoop steel equally between two faces; confirm governing code requirements and structural actions independently.")
    design_cols = st.columns(3)
    design_cols[0].metric("Peak required steel", f"{float(np.max(design_steel)):,.0f} mm²/m")
    design_cols[1].metric("Selected bar spacing", f"{provided_hoop_spacing:.0f} mm")
    design_cols[2].metric("Steel at selected spacing", f"{provided_hoop_steel:,.0f} mm²/m")
    if provided_hoop_steel < float(np.max(design_steel)):
        st.error("The selected bar size/spacing is below this preliminary estimate. This is not a final adequacy check.")
    else:
        st.warning("The selected bar size/spacing exceeds the simplified estimate only; this does not establish structural adequacy.")
    wall_fig = go.Figure()
    wall_fig.add_trace(go.Scatter(x=hoop_tension, y=depth, mode="lines", name="Hoop tension", line={"color": "#7c3aed", "width": 3}))
    wall_fig.update_layout(xaxis_title="Hoop tension (kN/m)", yaxis_title="Depth (m)", height=390, margin={"l": 20, "r": 20, "t": 20, "b": 20})
    wall_fig.update_yaxes(autorange="reversed")
    st.plotly_chart(wall_fig, use_container_width=True)
    st.dataframe(reinforcement_df.round(2), use_container_width=True, hide_index=True)

with tab_model:
    st.subheader("Schematic elevation and interactive geometry")
    left, right = st.columns(2)
    with left:
        elevation = go.Figure()
        elevation.add_trace(go.Scatter(x=[-radius, -radius, radius, radius], y=[0, cylinder_height, cylinder_height, 0], fill="toself", fillcolor="rgba(37,99,235,0.12)", line={"color": "#2563eb", "width": 3}, name="Cylindrical wall"))
        elevation.add_trace(go.Scatter(x=[-radius, -outlet_radius, outlet_radius, radius], y=[0, -hopper_height, -hopper_height, 0], fill="toself", fillcolor="rgba(234,88,12,0.18)", line={"color": "#ea580c", "width": 3}, name="Hopper"))
        elevation.add_trace(go.Scatter(x=[-radius - beam_width / 2, radius + beam_width / 2, radius + beam_width / 2, -radius - beam_width / 2, -radius - beam_width / 2], y=[0, 0, -beam_depth, -beam_depth, 0], fill="toself", fillcolor="rgba(100,116,139,0.35)", line={"color": "#475569"}, name="Ring beam (schematic)"))
        for angle in np.linspace(0, 2 * math.pi, int(number_of_columns), endpoint=False):
            x = (radius + column_width / 2) * math.cos(angle)
            if abs(x) > radius * 0.35:
                elevation.add_trace(go.Scatter(x=[x, x], y=[-beam_depth, -beam_depth-column_height], mode="lines", line={"color": "#334155", "width": 7}, showlegend=False))
        elevation.update_layout(title="Schematic elevation", xaxis_title="Width (m)", yaxis_title="Elevation (m)", height=470, showlegend=True, margin={"l": 20, "r": 20, "t": 50, "b": 20})
        elevation.update_yaxes(scaleanchor="x", scaleratio=1)
        st.plotly_chart(elevation, use_container_width=True)
    with right:
        theta = np.linspace(0, 2 * math.pi, 60)
        z_cyl = np.linspace(0, cylinder_height, 24)
        t_grid, z_grid = np.meshgrid(theta, z_cyl)
        fig3d = go.Figure()
        fig3d.add_trace(go.Surface(x=radius*np.cos(t_grid), y=radius*np.sin(t_grid), z=z_grid, colorscale=[[0, "#60a5fa"], [1, "#60a5fa"]], showscale=False, opacity=0.75, name="Wall"))
        z_hop = np.linspace(-hopper_height, 0, 18)
        t_hop, z_hop_grid = np.meshgrid(theta, z_hop)
        r_hop = outlet_radius + (radius-outlet_radius)*(z_hop_grid+hopper_height)/hopper_height
        fig3d.add_trace(go.Surface(x=r_hop*np.cos(t_hop), y=r_hop*np.sin(t_hop), z=z_hop_grid, colorscale=[[0, "#fb923c"], [1, "#fb923c"]], showscale=False, opacity=0.82, name="Hopper"))
        fig3d.update_layout(title="Interactive geometric model (schematic)", scene={"xaxis_title": "X (m)", "yaxis_title": "Y (m)", "zaxis_title": "Elevation (m)", "aspectmode": "data"}, height=470, margin={"l": 0, "r": 0, "t": 50, "b": 0})
        st.plotly_chart(fig3d, use_container_width=True)
    st.caption("Schematic geometry only; no construction detailing, tolerances, connection design, or structural adequacy is represented.")

with tab_bbs:
    st.subheader("Simplified reinforcement quantity schedule")
    st.caption("Approximate quantities based on the entered spacing and nominal geometry. Not a fabrication-ready bar bending schedule.")
    wall_centre_diameter = max(diameter - wall_thickness, 0.01)
    wall_circumference = math.pi * wall_centre_diameter
    wall_vertical_count = math.ceil(wall_circumference / (wall_vertical_spacing / 1000))
    wall_hoop_count = math.ceil(cylinder_height / (wall_hoop_spacing / 1000)) + 1
    hopper_bar_count = math.ceil(math.pi * max(diameter - hopper_thickness_mm / 1000, 0.01) / (hopper_spacing / 1000))
    hopper_ring_count = math.ceil(hopper_slant / (hopper_spacing / 1000)) + 1
    bbs_rows = [
        ("W1", "Wall vertical bars", int(wall_vertical_bar), wall_vertical_count, cylinder_height + lap_allowance),
        ("W2", "Wall hoop bars", int(wall_hoop_bar), wall_hoop_count, wall_circumference + lap_allowance),
        ("H1", "Hopper meridional bars", int(hopper_bar), hopper_bar_count, hopper_slant + lap_allowance),
    ]
    bbs = pd.DataFrame(bbs_rows, columns=["Mark", "Description", "Diameter (mm)", "Quantity", "Length each (m)"])
    bbs["Total length (m)"] = bbs["Quantity"] * bbs["Length each (m)"]
    bbs["Unit weight (kg/m)"] = bbs["Diameter (mm)"]**2 / 162
    bbs["Total weight (kg)"] = bbs["Total length (m)"] * bbs["Unit weight (kg/m)"]
    st.dataframe(bbs.round(2), use_container_width=True, hide_index=True)
    bbs_total = float(bbs["Total weight (kg)"].sum())
    st.metric("Estimated listed-bar weight", f"{bbs_total:,.1f} kg")
    bbs_summary = pd.DataFrame({"Measure": ["Total listed bar length", "Total listed bar weight"], "Value": [bbs["Total length (m)"].sum(), bbs_total], "Unit": ["m", "kg"]})
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        bbs.to_excel(writer, sheet_name="BBS", index=False)
        bbs_summary.to_excel(writer, sheet_name="Summary", index=False)
        geometry_df.to_excel(writer, sheet_name="Geometry", index=False)
        pressure_df.to_excel(writer, sheet_name="Pressure", index=False)
    st.download_button(
        "Download workbook (.xlsx)", data=excel_buffer.getvalue(),
        file_name="circular_rcc_bunker_preliminary_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

st.divider()
st.caption("Circular RCC Bunker Design Explorer · Streamlit deployment build · Verify all results independently before engineering use.")
