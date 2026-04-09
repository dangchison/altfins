import re
text1 = "TIA - Apr 08, 2026 - Trade setup: Price is consolidating"
m1 = re.search(r'([A-Z0-9\.]+)\s*-\s*(.*?)\s*-\s*Trade setup:', text1, re.IGNORECASE)
print("m1:", m1.groups() if m1 else None)

text2 = "Toncoin - Apr 08, 2026 - Trade setup: Price is consolidating"
m2 = re.search(r'([A-Z0-9\.]+)\s*-\s*(.*?)\s*-\s*Trade setup:', text2, re.IGNORECASE)
print("m2:", m2.groups() if m2 else None)
