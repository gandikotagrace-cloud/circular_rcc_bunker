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
        hopper_ring_bar = st.number_input("Hopper ring bar diameter (mm)", min_value=6, max_value=40, value=12, step=1)
        hopper_ring_spacing = st.number_input("Hopper ring bar spacing (mm)", min_value=25, max_value=500, value=150, step=5)
        ring_main_bar = st.number_input("Ring beam main bar diameter (mm)", min_value=6, max_value=40, value=16, step=1)
        ring_main_count = st.number_input("Ring beam main bar count", min_value=4, max_value=32, value=4, step=1)
        ring_stirrup_bar = st.number_input("Ring beam stirrup diameter (mm)", min_value=6, max_value=25, value=8, step=1)
        ring_stirrup_spacing = st.number_input("Ring beam stirrup spacing (mm)", min_value=25, max_value=500, value=150, step=5)
        column_main_bar = st.number_input("Column main bar diameter (mm)", min_value=6, max_value=40, value=16, step=1)
        column_main_count = st.number_input("Column main bars per column", min_value=4, max_value=32, value=8, step=1)
        column_tie_bar = st.number_input("Column tie diameter (mm)", min_value=6, max_value=25, value=8, step=1)
        column_tie_spacing = st.number_input("Column tie spacing (mm)", min_value=25, max_value=500, value=150, step=5)
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

tab_summary, tab_loads, tab_structure, tab_model, tab_reinforcement, tab_bbs = st.tabs([
    "Overview", "Pressure analysis", "Preliminary wall estimate", "Drawings & 3D", "Reinforcement detailing", "Quantity schedule"
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
    st.subheader("2D engineering drawings and interactive 3D model")
    st.caption("This geometry view follows the starter's Step 9 plan/elevation/section and Step 10 3D bunker arrangement.")

    drawing_plan, drawing_elevation, drawing_section, drawing_3d = st.tabs([
        "1. Top plan", "2. Front elevation", "3. Vertical section", "4. Interactive 3D model"
    ])

    sloping_length = math.hypot(hopper_height, radius - outlet_radius)
    hopper_dx = hopper_thickness * hopper_height / sloping_length
    hopper_dz = hopper_thickness * (radius - outlet_radius) / sloping_length

    with drawing_plan:
        plan = go.Figure()
        circle_theta = np.linspace(0, 2 * math.pi, 240)
        for r_value, color, dash, name, width in [
            (radius + beam_width / 2, "#111827", "solid", "Ring beam outer edge", 2.4),
            (max(radius - beam_width / 2, 0.001), "#111827", "dash", "Ring beam inner edge", 1.5),
            (radius, "#2563eb", "solid", "Wall outer face", 2.4),
            (radius - wall_thickness, "#2563eb", "dash", "Wall inner face", 1.5),
            (outlet_radius, "#dc2626", "solid", "Outlet", 2.0),
        ]:
            plan.add_trace(go.Scatter(
                x=r_value * np.cos(circle_theta), y=r_value * np.sin(circle_theta),
                mode="lines", line={"color": color, "dash": dash, "width": width}, name=name,
            ))
        for index in range(int(number_of_columns)):
            angle = 2 * math.pi * index / int(number_of_columns)
            local_corners = np.array([
                [-column_width / 2, -column_depth / 2],
                [column_width / 2, -column_depth / 2],
                [column_width / 2, column_depth / 2],
                [-column_width / 2, column_depth / 2],
                [-column_width / 2, -column_depth / 2],
            ])
            rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
            corners = local_corners @ rotation.T
            corners[:, 0] += radius * math.cos(angle)
            corners[:, 1] += radius * math.sin(angle)
            plan.add_trace(go.Scatter(
                x=corners[:, 0], y=corners[:, 1], mode="lines",
                line={"color": "#15803d", "width": 2}, fill="toself",
                fillcolor="rgba(21,128,61,0.06)", name="Support columns" if index == 0 else None,
                showlegend=index == 0,
            ))
        plan_limit = radius + beam_width + column_width + 1
        plan.update_layout(title="1. TOP PLAN", xaxis_title="X – Width (m)", yaxis_title="Y – Width (m)",
                           height=650, margin={"l": 20, "r": 20, "t": 55, "b": 20},
                           legend={"orientation": "h", "y": 1.12})
        plan.update_xaxes(range=[-plan_limit, plan_limit], showgrid=True, zeroline=False, scaleanchor="y", scaleratio=1)
        plan.update_yaxes(range=[-plan_limit, plan_limit], showgrid=True, zeroline=False)
        st.plotly_chart(plan, use_container_width=True)

    with drawing_elevation:
        elevation = go.Figure()
        def add_elevation_line(x_values, y_values, color, name, dash="solid", width=2):
            elevation.add_trace(go.Scatter(x=x_values, y=y_values, mode="lines", name=name,
                                           line={"color": color, "dash": dash, "width": width}))

        add_elevation_line([-radius, -radius], [0, cylinder_height], "#2563eb", "Wall outer face", width=2.5)
        add_elevation_line([radius, radius], [0, cylinder_height], "#2563eb", "", width=2.5)
        add_elevation_line([-radius + wall_thickness, -radius + wall_thickness], [0, cylinder_height], "#2563eb", "Wall inner face", "dash", 1.2)
        add_elevation_line([radius - wall_thickness, radius - wall_thickness], [0, cylinder_height], "#2563eb", "", "dash", 1.2)
        add_elevation_line([-radius, radius], [cylinder_height, cylinder_height], "#2563eb", "Top edge")
        add_elevation_line([-radius, radius], [0, 0], "#2563eb", "Bottom edge", width=1.5)
        add_elevation_line([-radius, -outlet_radius], [0, -hopper_height], "#ea580c", "Hopper outer face", width=2.5)
        add_elevation_line([radius, outlet_radius], [0, -hopper_height], "#ea580c", "", width=2.5)
        add_elevation_line([-radius + hopper_dx, -outlet_radius + hopper_dx], [hopper_dz, -hopper_height + hopper_dz], "#ea580c", "Hopper inner face", "dash", 1.2)
        add_elevation_line([radius - hopper_dx, outlet_radius - hopper_dx], [hopper_dz, -hopper_height + hopper_dz], "#ea580c", "", "dash", 1.2)
        for side in [-1, 1]:
            beam_x = side * radius - beam_width / 2
            elevation.add_trace(go.Scatter(
                x=[beam_x, beam_x + beam_width, beam_x + beam_width, beam_x, beam_x],
                y=[-beam_depth, -beam_depth, 0, 0, -beam_depth], mode="lines", fill="toself",
                fillcolor="rgba(156,163,175,0.55)", line={"color": "#111827", "width": 1.8},
                name="Ring beam" if side == -1 else None, showlegend=side == -1,
            ))
            column_x = side * radius - column_width / 2
            elevation.add_trace(go.Scatter(
                x=[column_x, column_x + column_width, column_x + column_width, column_x, column_x],
                y=[-beam_depth-column_height, -beam_depth-column_height, -beam_depth, -beam_depth, -beam_depth-column_height],
                mode="lines", fill="toself", fillcolor="rgba(148,163,184,0.55)",
                line={"color": "#111827", "width": 1.8},
                name="Support column" if side == -1 else None, showlegend=side == -1,
            ))
        add_elevation_line([-outlet_radius, -outlet_radius], [-hopper_height, -hopper_height-0.5], "#dc2626", "Outlet", width=2)
        add_elevation_line([outlet_radius, outlet_radius], [-hopper_height, -hopper_height-0.5], "#dc2626", "", width=2)
        add_elevation_line([-outlet_radius, outlet_radius], [-hopper_height-0.5, -hopper_height-0.5], "#dc2626", "", width=2)
        elevation.add_annotation(x=0, y=cylinder_height/2, text=f"CYLINDRICAL WALL<br>H = {cylinder_height:.2f} m", showarrow=False)
        elevation.add_annotation(x=0, y=-hopper_height/2, text=f"CONICAL HOPPER<br>H = {hopper_height:.2f} m", showarrow=False)
        elevation.add_annotation(x=radius+0.15, y=-beam_depth/2, text="Ring beam", showarrow=True, ax=55, ay=0)
        elevation.add_annotation(x=radius+0.15, y=-beam_depth-column_height/2, text="Support column", showarrow=True, ax=65, ay=0)
        side_limit = radius + column_width + 2.0
        elevation.update_layout(title="2. FRONT ELEVATION", xaxis_title="Width (m)", yaxis_title="Height (m)",
                                height=700, margin={"l": 20, "r": 20, "t": 55, "b": 20},
                                legend={"orientation": "h", "y": 1.12})
        elevation.update_xaxes(range=[-side_limit, side_limit], showgrid=True, zeroline=False, scaleanchor="y", scaleratio=1)
        elevation.update_yaxes(range=[-hopper_height-0.8-column_height-beam_depth, cylinder_height+1], showgrid=True, zeroline=False)
        st.plotly_chart(elevation, use_container_width=True)

    with drawing_section:
        section = go.Figure()
        section.add_trace(go.Scatter(x=[0, 0], y=[-hopper_height-0.8-column_height-beam_depth, cylinder_height+1],
                                     mode="lines", line={"color": "#6b7280", "dash": "dot", "width": 1}, name="Centre line"))
        for side in [-1, 1]:
            wall_x = [-radius, -radius+wall_thickness, -radius+wall_thickness, -radius] if side == -1 else [radius-wall_thickness, radius, radius, radius-wall_thickness]
            section.add_trace(go.Scatter(x=wall_x, y=[0, 0, cylinder_height, cylinder_height], mode="lines", fill="toself",
                                         fillcolor="rgba(125,211,252,0.55)", line={"color": "#2563eb", "width": 1.8},
                                         name="Cylindrical wall section" if side == -1 else None, showlegend=side == -1))
            hopper_x = [-radius, -radius+hopper_dx, -outlet_radius+hopper_dx, -outlet_radius] if side == -1 else [radius, radius-hopper_dx, outlet_radius-hopper_dx, outlet_radius]
            section.add_trace(go.Scatter(x=hopper_x, y=[0, hopper_dz, -hopper_height+hopper_dz, -hopper_height], mode="lines", fill="toself",
                                         fillcolor="rgba(253,230,138,0.7)", line={"color": "#ea580c", "width": 1.8},
                                         name="Hopper wall section" if side == -1 else None, showlegend=side == -1))
            beam_x = side * radius - beam_width / 2
            section.add_trace(go.Scatter(x=[beam_x, beam_x+beam_width, beam_x+beam_width, beam_x, beam_x],
                                         y=[-beam_depth, -beam_depth, 0, 0, -beam_depth], mode="lines", fill="toself",
                                         fillcolor="rgba(156,163,175,0.55)", line={"color": "#111827", "width": 1.8},
                                         name="Ring beam" if side == -1 else None, showlegend=side == -1))
            column_x = side * radius - column_width / 2
            section.add_trace(go.Scatter(x=[column_x, column_x+column_width, column_x+column_width, column_x, column_x],
                                         y=[-beam_depth-column_height, -beam_depth-column_height, -beam_depth, -beam_depth, -beam_depth-column_height],
                                         mode="lines", fill="toself", fillcolor="rgba(148,163,184,0.55)", line={"color": "#111827", "width": 1.8},
                                         name="Support column" if side == -1 else None, showlegend=side == -1))
        section.add_trace(go.Scatter(x=[-outlet_radius, outlet_radius, outlet_radius, -outlet_radius, -outlet_radius],
                                     y=[-hopper_height, -hopper_height, -hopper_height-0.5, -hopper_height-0.5, -hopper_height],
                                     mode="lines", fill="toself", fillcolor="rgba(248,113,113,0.65)", line={"color": "#dc2626", "width": 1.8}, name="Outlet"))
        section.add_annotation(x=0, y=cylinder_height/2, text="CYLINDRICAL<br>WALL", showarrow=False)
        section.add_annotation(x=0, y=-hopper_height/2, text="HOPPER", showarrow=False)
        section.add_annotation(x=0, y=-hopper_height-0.25, text="OUTLET", showarrow=False)
        section.update_layout(title="3. VERTICAL SECTION", xaxis_title="Width (m)", yaxis_title="Height (m)",
                              height=700, margin={"l": 20, "r": 20, "t": 55, "b": 20},
                              legend={"orientation": "h", "y": 1.12})
        section.update_xaxes(range=[-(radius+column_width+2), radius+column_width+2], showgrid=True, zeroline=False, scaleanchor="y", scaleratio=1)
        section.update_yaxes(range=[-hopper_height-0.8-column_height-beam_depth, cylinder_height+1], showgrid=True, zeroline=False)
        st.plotly_chart(section, use_container_width=True)

    with drawing_3d:
        theta = np.linspace(0, 2 * math.pi, 100)
        fig3d = go.Figure()
        z_cylinder = np.linspace(0, cylinder_height, 35)
        t_cylinder, z_cyl_grid = np.meshgrid(theta, z_cylinder)
        for r_wall, color, opacity, name in [
            (radius, "lightblue", 0.85, "Cylindrical Wall – Outer Face"),
            (radius-wall_thickness, "deepskyblue", 0.75, "Cylindrical Wall – Inner Face"),
        ]:
            fig3d.add_trace(go.Surface(x=r_wall*np.cos(t_cylinder), y=r_wall*np.sin(t_cylinder), z=z_cyl_grid,
                                        colorscale=[[0, color], [1, color]], showscale=False, opacity=opacity, name=name))

        z_hopper = np.linspace(-hopper_height, 0, 35)
        t_hopper, z_hop_grid = np.meshgrid(theta, z_hopper)
        outer_hopper_radius = outlet_radius + (radius-outlet_radius)*(z_hop_grid+hopper_height)/hopper_height
        fig3d.add_trace(go.Surface(x=outer_hopper_radius*np.cos(t_hopper), y=outer_hopper_radius*np.sin(t_hopper), z=z_hop_grid,
                                    colorscale=[[0, "orange"], [1, "orange"]], showscale=False, opacity=0.9, name="Conical Hopper – Outer Face"))
        inner_hopper_radius = outer_hopper_radius - hopper_dx
        fig3d.add_trace(go.Surface(x=inner_hopper_radius*np.cos(t_hopper), y=inner_hopper_radius*np.sin(t_hopper), z=z_hop_grid+hopper_dz,
                                    colorscale=[[0, "gold"], [1, "gold"]], showscale=False, opacity=0.75, name="Conical Hopper – Inner Face"))

        ring_outer_radius = radius + beam_width/2
        ring_inner_radius = max(radius-beam_width/2, 0.001)
        radial_values = np.linspace(ring_inner_radius, ring_outer_radius, 12)
        t_ring, radial_grid = np.meshgrid(theta, radial_values)
        for z_level, name in [(0, "Ring Beam – Top"), (-beam_depth, "Ring Beam – Bottom")]:
            fig3d.add_trace(go.Surface(x=radial_grid*np.cos(t_ring), y=radial_grid*np.sin(t_ring), z=np.full_like(radial_grid, z_level),
                                        colorscale=[[0, "dimgray"], [1, "dimgray"]], showscale=False, opacity=1, name=name))
        t_side, z_side = np.meshgrid(theta, np.linspace(-beam_depth, 0, 8))
        for r_side, name in [(ring_outer_radius, "Ring Beam – Outer Face"), (ring_inner_radius, "Ring Beam – Inner Face")]:
            fig3d.add_trace(go.Surface(x=r_side*np.cos(t_side), y=r_side*np.sin(t_side), z=z_side,
                                        colorscale=[[0, "gray"], [1, "gray"]], showscale=False, opacity=1, name=name))

        local_column = np.array([[-column_width/2, -column_depth/2], [column_width/2, -column_depth/2],
                                 [column_width/2, column_depth/2], [-column_width/2, column_depth/2]])
        mesh_i = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
        mesh_j = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
        mesh_k = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]
        column_radius = radius + column_width/2
        for index in range(int(number_of_columns)):
            angle = 2 * math.pi * index / int(number_of_columns)
            rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
            corners = local_column @ rotation.T
            corners[:, 0] += column_radius * math.cos(angle)
            corners[:, 1] += column_radius * math.sin(angle)
            fig3d.add_trace(go.Mesh3d(
                x=np.concatenate([corners[:, 0], corners[:, 0]]), y=np.concatenate([corners[:, 1], corners[:, 1]]),
                z=[-beam_depth-column_height]*4 + [-beam_depth]*4,
                i=mesh_i, j=mesh_j, k=mesh_k, color="gray", opacity=1,
                name="RCC Support Columns" if index == 0 else None, showlegend=index == 0,
            ))

        z_outlet = np.linspace(-hopper_height-0.6, -hopper_height, 8)
        t_outlet, z_outlet_grid = np.meshgrid(theta, z_outlet)
        fig3d.add_trace(go.Surface(x=outlet_radius*np.cos(t_outlet), y=outlet_radius*np.sin(t_outlet), z=z_outlet_grid,
                                    colorscale=[[0, "lightcoral"], [1, "lightcoral"]], showscale=False, opacity=0.95, name="Outlet Pipe"))
        fig3d.add_trace(go.Scatter3d(x=[0, 0], y=[0, 0], z=[-hopper_height-0.6, cylinder_height], mode="lines",
                                     line={"color": "black", "width": 2, "dash": "dash"}, name="Centre Line"))
        fig3d.update_layout(title={"text": "CIRCULAR RCC BUNKER – INTERACTIVE 3D MODEL", "x": 0.5},
                            scene={"xaxis_title": "X (m)", "yaxis_title": "Y (m)", "zaxis_title": "Height (m)",
                                   "aspectmode": "data", "camera": {"eye": {"x": 1.7, "y": 1.7, "z": 1.3}}},
                            height=800, margin={"l": 0, "r": 0, "t": 60, "b": 0},
                            legend={"orientation": "h", "y": -0.1})
        st.plotly_chart(fig3d, use_container_width=True)

    st.caption("Schematic geometry only, matching the source drawing arrangement. These figures are not construction drawings and do not verify structural adequacy.")

with tab_reinforcement:
    st.subheader("Reinforcement arrangement — notebook Step 14 style")
    st.warning(
        "These are schematic reinforcement placement views based on the entered bar sizes and spacing. "
        "They do not verify development length, laps, anchorage, cover, congestion, or structural adequacy."
    )
    rebar_elevation_tab, rebar_plan_tab, rebar_3d_tab = st.tabs([
        "2D elevation", "2D plan", "3D reinforcement model"
    ])

    cover = concrete_cover_mm / 1000
    wall_vertical_spacing_m = wall_vertical_spacing / 1000
    wall_hoop_spacing_m = wall_hoop_spacing / 1000
    hopper_meridional_spacing_m = hopper_spacing / 1000
    hopper_ring_spacing_m = hopper_ring_spacing / 1000
    ring_stirrup_spacing_m = ring_stirrup_spacing / 1000
    column_tie_spacing_m = column_tie_spacing / 1000

    # Follow the notebook's Step 14 bar layout rules and keep Plotly traces grouped
    # by bar family to avoid creating hundreds of separate browser traces.
    wall_bar_count = max(8, int(math.ceil(math.pi * diameter / wall_vertical_spacing_m)))
    wall_angles = np.linspace(0, 2 * math.pi, wall_bar_count, endpoint=False)
    wall_hoop_levels = np.arange(wall_hoop_spacing_m / 2, cylinder_height, wall_hoop_spacing_m)
    hopper_meridional_count = max(8, int(math.ceil(math.pi * diameter / hopper_meridional_spacing_m)))
    hopper_angles = np.linspace(0, 2 * math.pi, hopper_meridional_count, endpoint=False)
    hopper_ring_levels = np.arange(hopper_ring_spacing_m, hopper_height, hopper_ring_spacing_m)
    column_radius = radius * 0.75
    column_angles = np.linspace(0, 2 * math.pi, int(number_of_columns), endpoint=False)
    column_x = column_radius * np.cos(column_angles)
    column_y = column_radius * np.sin(column_angles)
    ring_beam_top_z = 0.0
    ring_beam_bottom_z = -beam_depth
    column_top_z = ring_beam_bottom_z
    column_bottom_z = column_top_z - column_height

    def perimeter_bar_points(width_m, depth_m, count):
        """Place count points uniformly around a rectangular bar perimeter."""
        corners = np.array([
            [-width_m / 2, -depth_m / 2],
            [width_m / 2, -depth_m / 2],
            [width_m / 2, depth_m / 2],
            [-width_m / 2, depth_m / 2],
            [-width_m / 2, -depth_m / 2],
        ])
        lengths = np.linalg.norm(np.diff(corners, axis=0), axis=1)
        perimeter = float(lengths.sum())
        points = []
        for index in range(int(count)):
            distance = index * perimeter / int(count)
            for side_index, side_length in enumerate(lengths):
                if distance <= side_length + 1e-9:
                    fraction = distance / side_length
                    points.append(corners[side_index] + fraction * (corners[side_index + 1] - corners[side_index]))
                    break
                distance -= side_length
        return np.asarray(points)

    ring_bar_clearance = cover + ring_stirrup_bar / 1000 + ring_main_bar / 2000
    beam_bar_width = max(0.01, beam_width - 2 * ring_bar_clearance)
    beam_bar_depth = max(0.01, beam_depth - 2 * ring_bar_clearance)
    beam_bar_points = perimeter_bar_points(beam_bar_width, beam_bar_depth, int(ring_main_count))
    beam_mid_z = (ring_beam_top_z + ring_beam_bottom_z) / 2
    ring_beam_bar_paths = [
        {"radius": radius + float(point[0]), "z": beam_mid_z + float(point[1])}
        for point in beam_bar_points
    ]
    ring_stirrup_count = max(1, int(math.ceil(2 * math.pi * radius / ring_stirrup_spacing_m)))
    ring_stirrup_angles = np.linspace(0, 2 * math.pi, ring_stirrup_count, endpoint=False)
    stirrup_radial_half = max(0.01, beam_width / 2 - cover - ring_stirrup_bar / 2000)
    column_bar_clearance = cover + column_tie_bar / 1000 + column_main_bar / 2000
    column_bar_width = max(0.01, column_width - 2 * column_bar_clearance)
    column_bar_depth = max(0.01, column_depth - 2 * column_bar_clearance)
    column_bar_points = perimeter_bar_points(column_bar_width, column_bar_depth, int(column_main_count))
    column_tie_levels = np.arange(
        column_bottom_z + column_tie_spacing_m / 2,
        column_top_z,
        column_tie_spacing_m,
    )
    theta_detail = np.linspace(0, 2 * math.pi, 160)

    def add_2d_segment_family(figure, segments, name, color, width=1.5, dash="solid"):
        x_values, y_values = [], []
        for x_segment, y_segment in segments:
            x_values.extend(x_segment)
            y_values.extend(y_segment)
            x_values.append(None)
            y_values.append(None)
        if x_values:
            figure.add_trace(go.Scatter(
                x=x_values, y=y_values, mode="lines", name=name,
                line={"color": color, "width": width, "dash": dash},
            ))

    def add_3d_segment_family(figure, segments, name, color, width=3):
        x_values, y_values, z_values = [], [], []
        for x_segment, y_segment, z_segment in segments:
            x_values.extend(x_segment)
            y_values.extend(y_segment)
            z_values.extend(z_segment)
            x_values.append(None)
            y_values.append(None)
            z_values.append(None)
        if x_values:
            figure.add_trace(go.Scatter3d(
                x=x_values, y=y_values, z=z_values, mode="lines", name=name,
                line={"color": color, "width": width},
            ))

    with rebar_elevation_tab:
        elevation_rebar = go.Figure()
        add_2d_segment_family(elevation_rebar, [([-radius, -radius], [0, cylinder_height]), ([radius, radius], [0, cylinder_height])], "Wall", "#111827", 2.2)
        add_2d_segment_family(elevation_rebar, [([-radius, -outlet_radius], [0, -hopper_height]), ([radius, outlet_radius], [0, -hopper_height])], "Hopper", "#111827", 2.2)
        add_2d_segment_family(elevation_rebar, [([-outlet_radius, outlet_radius], [-hopper_height, -hopper_height])], "Outlet", "#111827", 2)

        wall_vertical_elevation = []
        for angle in [0, math.pi]:
            x_pos = radius * math.cos(angle)
            wall_vertical_elevation.append(([x_pos, x_pos], [0, cylinder_height]))
        add_2d_segment_family(elevation_rebar, wall_vertical_elevation, f"Wall vertical bars ({wall_vertical_bar} mm)", "#dc2626", 2)
        add_2d_segment_family(elevation_rebar, [([-radius, radius], [float(z), float(z)]) for z in wall_hoop_levels], f"Wall hoop bars ({wall_hoop_bar} mm @ {wall_hoop_spacing} mm)", "#2563eb", 1)
        hopper_meridional_elevation = [
            ([radius * math.cos(angle), outlet_radius * math.cos(angle)], [0, -hopper_height])
            for angle in [0, math.pi]
        ]
        add_2d_segment_family(elevation_rebar, hopper_meridional_elevation, f"Hopper meridional bars ({hopper_bar} mm)", "#16a34a", 2)
        add_2d_segment_family(
            elevation_rebar,
            [([-r_level, r_level], [-float(z), -float(z)]) for z in hopper_ring_levels
             for r_level in [radius - (float(z) / hopper_height) * (radius - outlet_radius)]],
            f"Hopper ring bars ({hopper_ring_bar} mm)", "#9333ea", 1.4,
        )

        beam_outline = [([-radius-beam_width/2, radius+beam_width/2, radius+beam_width/2, -radius-beam_width/2, -radius-beam_width/2],
                         [0, 0, -beam_depth, -beam_depth, 0])]
        add_2d_segment_family(elevation_rebar, beam_outline, "Ring beam concrete", "#f97316", 6)
        beam_bar_segments = []
        for bar in ring_beam_bar_paths:
            z_pos = ring_beam_top_z - ring_bar_clearance if bar["z"] >= beam_mid_z else ring_beam_bottom_z + ring_bar_clearance
            beam_bar_segments.append(([-radius, radius], [z_pos, z_pos]))
        add_2d_segment_family(elevation_rebar, beam_bar_segments, f"Ring beam main bars ({ring_main_bar} mm)", "#991b1b", 2.2)
        add_2d_segment_family(
            elevation_rebar,
            [([-radius + (2*radius)*i/max(1, ring_stirrup_count-1)] * 2,
              [ring_beam_bottom_z + cover, ring_beam_top_z - cover]) for i in range(ring_stirrup_count)],
            f"Ring beam stirrups ({ring_stirrup_bar} mm @ {ring_stirrup_spacing} mm)", "#ea580c", 1,
        )

        column_segments = [([float(x), float(x)], [column_top_z, column_bottom_z]) for x in column_x]
        add_2d_segment_family(elevation_rebar, column_segments, "Support columns", "rgba(120,53,15,0.65)", 7)
        column_main_segments = [
            ([float(x + point[0]), float(x + point[0])], [column_bottom_z, column_top_z])
            for x in column_x for point in column_bar_points
        ]
        add_2d_segment_family(elevation_rebar, column_main_segments, f"Column main bars ({column_main_bar} mm)", "#7f1d1d", 1.5)
        column_tie_segments = [
            ([float(x-column_width/2+cover), float(x+column_width/2-cover)], [float(z), float(z)])
            for x in column_x for z in column_tie_levels
        ]
        add_2d_segment_family(elevation_rebar, column_tie_segments, f"Column ties ({column_tie_bar} mm @ {column_tie_spacing} mm)", "#f97316", 1)
        elevation_rebar.update_layout(
            title="2D Reinforcement Elevation — Circular RCC Bunker",
            xaxis_title="Horizontal distance (m)", yaxis_title="Vertical elevation (m)",
            height=760, margin={"l": 25, "r": 20, "t": 55, "b": 25},
            legend={"orientation": "h", "y": 1.12},
        )
        elevation_rebar.update_xaxes(scaleanchor="y", scaleratio=1, showgrid=True, zeroline=False)
        elevation_rebar.update_yaxes(range=[column_bottom_z-0.8, cylinder_height+0.8], showgrid=True, zeroline=False)
        st.plotly_chart(elevation_rebar, use_container_width=True)

    with rebar_plan_tab:
        plan_rebar = go.Figure()
        plan_circle = np.linspace(0, 2 * math.pi, 240)
        add_2d_segment_family(plan_rebar, [(radius*np.cos(plan_circle), radius*np.sin(plan_circle))], "Bunker wall", "#111827", 2.2)
        add_2d_segment_family(plan_rebar, [((radius-wall_thickness)*np.cos(plan_circle), (radius-wall_thickness)*np.sin(plan_circle))], "Wall inner face", "#6b7280", 1, "dash")
        plan_rebar.add_trace(go.Scatter(x=radius*np.cos(wall_angles), y=radius*np.sin(wall_angles), mode="markers",
                                        marker={"color": "#dc2626", "size": 6}, name=f"Wall vertical bars ({wall_vertical_bar} mm)"))
        for hoop_radius in [radius*0.35, radius*0.60, radius*0.85]:
            add_2d_segment_family(plan_rebar, [(hoop_radius*np.cos(plan_circle), hoop_radius*np.sin(plan_circle))],
                                  "Wall hoop reinforcement", "#2563eb", 1)
        for ring_radius, color, name, width in [
            (radius+beam_width/2, "#f97316", "Ring beam boundary", 2),
            (max(radius-beam_width/2, 0.01), "#f97316", "", 2),
        ]:
            add_2d_segment_family(plan_rebar, [(ring_radius*np.cos(plan_circle), ring_radius*np.sin(plan_circle))], name, color, width)
        for bar_index, bar in enumerate(ring_beam_bar_paths):
            add_2d_segment_family(plan_rebar, [(bar["radius"]*np.cos(plan_circle), bar["radius"]*np.sin(plan_circle))],
                                  "Ring beam longitudinal bars" if bar_index == 0 else "", "#991b1b", 1.5)
        stirrup_segments_plan = []
        for angle in ring_stirrup_angles:
            stirrup_segments_plan.append((
                [(radius-stirrup_radial_half)*math.cos(angle), (radius+stirrup_radial_half)*math.cos(angle)],
                [(radius-stirrup_radial_half)*math.sin(angle), (radius+stirrup_radial_half)*math.sin(angle)],
            ))
        add_2d_segment_family(plan_rebar, stirrup_segments_plan, f"Ring beam stirrups ({ring_stirrup_bar} mm)", "#ea580c", 1)

        column_rectangles = []
        column_main_points_plan = []
        tie_rectangles_plan = []
        for x, y in zip(column_x, column_y):
            rect_x = [x-column_width/2, x+column_width/2, x+column_width/2, x-column_width/2, x-column_width/2]
            rect_y = [y-column_depth/2, y-column_depth/2, y+column_depth/2, y+column_depth/2, y-column_depth/2]
            column_rectangles.append((rect_x, rect_y))
            tie_w = max(0.01, column_width - 2*cover)
            tie_d = max(0.01, column_depth - 2*cover)
            tie_rectangles_plan.append(([x-tie_w/2, x+tie_w/2, x+tie_w/2, x-tie_w/2, x-tie_w/2],
                                        [y-tie_d/2, y-tie_d/2, y+tie_d/2, y+tie_d/2, y-tie_d/2]))
            for point in column_bar_points:
                column_main_points_plan.append((x+point[0], y+point[1]))
        add_2d_segment_family(plan_rebar, column_rectangles, "Column sections", "rgba(120,53,15,0.65)", 2)
        add_2d_segment_family(plan_rebar, tie_rectangles_plan, "Column closed ties", "#ea580c", 1.5)
        if column_main_points_plan:
            plan_rebar.add_trace(go.Scatter(
                x=[point[0] for point in column_main_points_plan], y=[point[1] for point in column_main_points_plan],
                mode="markers", marker={"color": "#7f1d1d", "size": 6},
                name=f"Column main bars ({column_main_bar} mm)",
            ))
        plan_limit = radius + beam_width + column_width + 1
        plan_rebar.update_layout(title="2D Reinforcement Plan — Circular RCC Bunker", xaxis_title="X direction (m)",
                                 yaxis_title="Y direction (m)", height=720,
                                 margin={"l": 20, "r": 20, "t": 55, "b": 20},
                                 legend={"orientation": "h", "y": 1.12})
        plan_rebar.update_xaxes(range=[-plan_limit, plan_limit], scaleanchor="y", scaleratio=1, showgrid=True)
        plan_rebar.update_yaxes(range=[-plan_limit, plan_limit], showgrid=True)
        st.plotly_chart(plan_rebar, use_container_width=True)

    with rebar_3d_tab:
        fig_rebar_3d = go.Figure()
        ring_outer_radius = radius + beam_width / 2
        ring_inner_radius = max(0.01, radius - beam_width / 2)
        ring_theta_grid, ring_radius_grid = np.meshgrid(
            theta_detail, np.linspace(ring_inner_radius, ring_outer_radius, 10)
        )
        for z_level in [ring_beam_top_z, ring_beam_bottom_z]:
            fig_rebar_3d.add_trace(go.Surface(
                x=ring_radius_grid*np.cos(ring_theta_grid),
                y=ring_radius_grid*np.sin(ring_theta_grid),
                z=np.full_like(ring_radius_grid, z_level),
                colorscale=[[0, "orange"], [1, "orange"]],
                showscale=False, opacity=0.25, name="Ring beam concrete",
                showlegend=z_level == ring_beam_top_z,
            ))
        ring_face_theta, ring_face_z = np.meshgrid(
            theta_detail, np.linspace(ring_beam_bottom_z, ring_beam_top_z, 8)
        )
        for face_radius in [ring_outer_radius, ring_inner_radius]:
            fig_rebar_3d.add_trace(go.Surface(
                x=face_radius*np.cos(ring_face_theta),
                y=face_radius*np.sin(ring_face_theta), z=ring_face_z,
                colorscale=[[0, "orange"], [1, "orange"]],
                showscale=False, opacity=0.18, name="Ring beam concrete", showlegend=False,
            ))

        wall_vertical_3d = []
        for angle in wall_angles:
            x_pos, y_pos = radius*math.cos(angle), radius*math.sin(angle)
            wall_vertical_3d.append(([x_pos, x_pos], [y_pos, y_pos], [0, cylinder_height]))
        add_3d_segment_family(fig_rebar_3d, wall_vertical_3d, f"Wall vertical bars ({wall_vertical_bar} mm)", "#dc2626", 3)
        wall_hoop_3d = [
            (radius*np.cos(theta_detail), radius*np.sin(theta_detail), np.full_like(theta_detail, float(z)))
            for z in wall_hoop_levels
        ]
        add_3d_segment_family(fig_rebar_3d, wall_hoop_3d, f"Wall hoop bars ({wall_hoop_bar} mm)", "#2563eb", 3)
        hopper_meridional_3d = [
            ([radius*math.cos(angle), outlet_radius*math.cos(angle)],
             [radius*math.sin(angle), outlet_radius*math.sin(angle)], [0, -hopper_height])
            for angle in hopper_angles
        ]
        add_3d_segment_family(fig_rebar_3d, hopper_meridional_3d, f"Hopper meridional bars ({hopper_bar} mm)", "#16a34a", 4)
        hopper_ring_3d = []
        for level in hopper_ring_levels:
            ring_radius = radius - (float(level)/hopper_height)*(radius-outlet_radius)
            hopper_ring_3d.append((ring_radius*np.cos(theta_detail), ring_radius*np.sin(theta_detail), np.full_like(theta_detail, -float(level))))
        add_3d_segment_family(fig_rebar_3d, hopper_ring_3d, f"Hopper ring bars ({hopper_ring_bar} mm)", "#9333ea", 3)

        beam_main_3d = [
            (bar["radius"]*np.cos(theta_detail), bar["radius"]*np.sin(theta_detail), np.full_like(theta_detail, bar["z"]))
            for bar in ring_beam_bar_paths
        ]
        add_3d_segment_family(fig_rebar_3d, beam_main_3d, f"Ring beam longitudinal bars ({ring_main_bar} mm)", "#991b1b", 5)
        beam_stirrups_3d = []
        for angle in ring_stirrup_angles:
            radial = [radius-stirrup_radial_half, radius+stirrup_radial_half, radius+stirrup_radial_half,
                      radius-stirrup_radial_half, radius-stirrup_radial_half]
            z_path = [ring_beam_bottom_z+cover, ring_beam_bottom_z+cover, ring_beam_top_z-cover,
                      ring_beam_top_z-cover, ring_beam_bottom_z+cover]
            beam_stirrups_3d.append(([r*math.cos(angle) for r in radial], [r*math.sin(angle) for r in radial], z_path))
        add_3d_segment_family(fig_rebar_3d, beam_stirrups_3d, f"Ring beam stirrups ({ring_stirrup_bar} mm)", "#ea580c", 3)

        column_concrete_3d = []
        column_main_3d = []
        for x, y in zip(column_x, column_y):
            column_concrete_3d.append(([float(x), float(x)], [float(y), float(y)], [column_top_z, column_bottom_z]))
            for point in column_bar_points:
                x_bar, y_bar = float(x+point[0]), float(y+point[1])
                column_main_3d.append(([x_bar, x_bar], [y_bar, y_bar], [column_bottom_z, column_top_z]))
        add_3d_segment_family(fig_rebar_3d, column_concrete_3d, "Supporting columns", "#8b4513", 10)
        add_3d_segment_family(fig_rebar_3d, column_main_3d, f"Column main bars ({column_main_bar} mm)", "#7f1d1d", 5)
        column_ties_3d = []
        tie_half_w = max(0.01, column_width/2-cover-column_tie_bar/2000)
        tie_half_d = max(0.01, column_depth/2-cover-column_tie_bar/2000)
        tie_local_x = [-tie_half_w, tie_half_w, tie_half_w, -tie_half_w, -tie_half_w]
        tie_local_y = [-tie_half_d, -tie_half_d, tie_half_d, tie_half_d, -tie_half_d]
        for x, y in zip(column_x, column_y):
            for z_level in column_tie_levels:
                column_ties_3d.append(([float(x)+v for v in tie_local_x], [float(y)+v for v in tie_local_y], [float(z_level)]*5))
        add_3d_segment_family(fig_rebar_3d, column_ties_3d, f"Column ties ({column_tie_bar} mm)", "#f97316", 3)

        fig_rebar_3d.update_layout(
            title="3D Reinforcement Model — Circular RCC Bunker",
            scene={"xaxis_title": "X (m)", "yaxis_title": "Y (m)", "zaxis_title": "Elevation (m)",
                   "aspectmode": "data"},
            height=850, margin={"l": 0, "r": 0, "t": 60, "b": 0},
            legend={"orientation": "h", "y": 1.12},
        )
        st.plotly_chart(fig_rebar_3d, use_container_width=True)

    st.caption(
        f"Displayed bars: {wall_bar_count} wall vertical positions, {len(wall_hoop_levels)} wall hoop levels, "
        f"{hopper_meridional_count} hopper meridional bars, {len(hopper_ring_levels)} hopper ring levels, "
        f"{int(number_of_columns)} support columns. All detailing is schematic and unverified."
    )

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
