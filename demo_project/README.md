# Monkez Runtime Demo

Du an nay minh hoa cach ung dung PyQt6 load truc tiep file `.ui` co Monkez custom widgets.
Designer portable chi can cho buoc thiet ke giao dien; may chay ung dung chi can cai Python package.

## Chay ngay trong repository

```powershell
cd demo_project
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ..
.\.venv\Scripts\python.exe main.py
```

## Chay nhu mot project doc lap

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`main.py` dung `PyQt6.uic.loadUi()` de load [ui/main_window.ui](ui/main_window.ui).
Custom widget classes duoc resolve tu header:

```xml
<header>custom_pyqt6_designer.monkez_widgets</header>
```

Khong can copy source widget vao project va khong can dat Designer executable canh ung dung.
