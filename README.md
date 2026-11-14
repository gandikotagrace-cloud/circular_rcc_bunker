Circular RCC Bunker Streamlit App
This folder contains a Streamlit deployment build of the notebook-export starter. The original `circular_rcc_hopper_bunker_design_starter.py` is retained as a reference; run the Streamlit version from `app.py`.
Run locally
Open a terminal in this folder.
Create and activate a virtual environment if desired.
Install dependencies with `pip install -r requirements.txt`.
Start the app with `streamlit run app.py`.
Deploy on Streamlit Community Cloud
Push this folder to a GitHub repository.
In Streamlit Community Cloud, select Create app and choose the repository and branch.
Set the Main file path to `app.py`.
Deploy. The platform installs packages from `requirements.txt`.
Scope and engineering caution
The Streamlit app provides preliminary geometry and quantity calculations, a Janssen-type cylindrical pressure profile, a simplified hoop-steel estimate, schematic plots, and an approximate bar quantity workbook. It does not implement every module in the original starter, and the calculations are not a complete code-compliant structural design. In particular, hopper loading, load combinations, wall bending/shear/crack checks, seismic and wind analysis, support-frame actions, and foundation design are not verified. A qualified structural engineer must independently validate methods, assumptions, code editions, and all results before design or construction use
