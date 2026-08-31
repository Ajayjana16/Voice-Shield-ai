import os

frontend_dir = r"d:\New folder (2)\frontend"
for root, dirs, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith((".js", ".jsx", ".ts", ".tsx", ".html")):
            p = os.path.join(root, file)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for needle in ["live-monitoring", "live_monitoring", "/live", "activeTab", "activeMode"]:
                    if needle in content:
                        print(f"{file}: {needle}")
