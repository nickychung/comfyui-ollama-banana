
import random
import unittest

def parse_single_line(line):
    line = line.strip()
    if not line: return ""
    words = line.split()
    if len(words) > 10:
        return " ".join(words[:10]) + "..."
    return line

def parse_all_txt_chunk(chunk):
    chunk = chunk.strip()
    if not chunk: return ""
    
    lines = chunk.split('\n')
    short_map = {"Subject": "Sub", "Composition": "Com", "Action": "Act", "Location": "Loc", "Style": "Sty"}
    label_parts = []
    
    theme_line = next((l for l in lines if l.startswith("Theme:")), None)
    if theme_line:
        val = theme_line.split(":", 1)[1].strip()
        # Random 3 words
        words = val.split()
        if words:
            # Deterministic seed based on the value string
            rng = random.Random(val)
            if len(words) > 3:
                chosen = rng.sample(words, 3)
                # Keep original order for readability? Or purely random order? 
                # User said "randomly choose three words". 
                # Usually keeping relative order is nicer but "randomly choose" implies sample.
                # Let's try to keep them in original relative order if possible for readability, 
                # but sample doesn't guarantee that. 
                # Let's just join the chosen ones.
                short_val = " ".join(chosen)
            else:
                short_val = " ".join(words)
            label_parts.append(f"Thm: {short_val}")

    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            if k in short_map:
                words = v.split()
                if words:
                   rng = random.Random(v)
                   if len(words) > 3:
                       chosen = rng.sample(words, 3)
                       short_val = " ".join(chosen)
                   else:
                       short_val = " ".join(words)
                   
                   label_parts.append(f"{short_map[k]}: {short_val}")
    
    if not label_parts:
        return " ".join(chunk.split()[:5]) + "..."
    
    return ", ".join(label_parts)

class TestLabelGeneration(unittest.TestCase):
    def test_single_line_short(self):
        self.assertEqual(parse_single_line("hello world"), "hello world")
        
    def test_single_line_long(self):
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11"
        expected = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10..."
        self.assertEqual(parse_single_line(text), expected)

    def test_all_txt_deterministic(self):
        chunk = """Theme: A futuristic city with flying cars
Subject: A robot detective solving a crime
Action: inspecting a clue
"""
        label1 = parse_all_txt_chunk(chunk)
        label2 = parse_all_txt_chunk(chunk)
        print(f"Label: {label1}")
        self.assertEqual(label1, label2)
        
    def test_all_txt_content(self):
        chunk = "Subject: One two three four five six"
        label = parse_all_txt_chunk(chunk)
        print(f"Label Random: {label}")
        self.assertIn("Sub:", label)
        # Should have 3 words
        self.assertEqual(len(label.split()), 4) # Sub: w1 w2 w3

if __name__ == '__main__':
    unittest.main()
