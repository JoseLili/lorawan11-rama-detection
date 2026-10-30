from pathlib import Path
for line in Path("/content/barcelona/worker.log").read_text(errors="replace").splitlines()[-65:]:
 if not any(x in line for x in ["http","token"]):print(line)
