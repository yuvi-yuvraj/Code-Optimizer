# OptiCode — C++ Code Optimizer

A college-level Compiler Design project: a Flask web dashboard with an educational C++ optimization engine.

## Requirements
- Python 3.9+
- pip
- Optional: g++ (MinGW-w64 on Windows) or clang++ for C++ syntax validation

## Run on Windows (PowerShell)
1. Extract the ZIP.
2. Open the extracted `cpp_code_optimizer` folder in VS Code.
3. Open Terminal > New Terminal.
4. Create a virtual environment:
   ```powershell
   py -m venv venv
   ```
5. Activate it:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   ```
6. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
7. Start the app:
   ```powershell
   python app.py
   ```
8. Open `http://127.0.0.1:5000` in your browser.
9. Click **Load sample**, then **Optimize Code**.

## Project structure
- `app.py` — Flask routes and API
- `optimizer.py` — optimization passes
- `templates/index.html` — dashboard layout
- `static/style.css` — dashboard styling
- `static/app.js` — frontend interactions
- `sample.cpp` — sample input

## Current optimization scope
- Constant folding for numeric arithmetic expressions
- Constant/copy propagation in straight-line statements
- Basic algebraic simplification
- Conservative dead assignment removal for unused constant assignments
- Simple common-subexpression reuse

## Important limitations
This is a teaching prototype, not a complete C++ parser or production compiler. It does not perform full control-flow/data-flow analysis, preserve all C++ side-effect semantics, or optimize arbitrary templates, pointers, references, classes, macros, or complex expressions. Use the validator and test behavior before relying on output. The strength-reduction panel is an extension point; it is not currently applied by the engine.
