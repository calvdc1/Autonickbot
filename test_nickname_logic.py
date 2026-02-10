
import unittest

class TestNicknameLogic(unittest.TestCase):
    def calculate_nickname(self, current_nick, target_tag, all_known_tags):
        # Logic from bot.py
        temp_nick = current_nick
        
        # Sort by length descending to avoid partial replacements
        all_known_tags.sort(key=len, reverse=True)
        
        for tag in all_known_tags:
            if tag in temp_nick:
                # Try removing " {tag}" (with space)
                new_val = temp_nick.replace(f" {tag}", "")
                if new_val == temp_nick:
                    # Try removing "{tag}" (no space)
                    new_val = temp_nick.replace(tag, "")
                temp_nick = new_val.strip()
                
        # Now temp_nick should be just the username without any known tags
        
        # --- 3. Append Target Tag ---
        if target_tag:
            final_nick = f"{temp_nick} {target_tag}"
        else:
            final_nick = temp_nick

        # --- 4. Length Check (32 chars max) ---
        if len(final_nick) > 32:
            if target_tag:
                # Truncate name to fit tag
                allowed_len = 32 - len(target_tag) - 1 # -1 for space
                if allowed_len > 0:
                    final_nick = f"{temp_nick[:allowed_len].strip()} {target_tag}"
                else:
                    final_nick = temp_nick[:32] # Fallback
            else:
                final_nick = temp_nick[:32]
        
        return final_nick

    def test_basic_enforcement(self):
        # User manually removes tag
        # Config: Target=[Tag], Known=[[Tag]]
        # Input: "Name"
        # Output: "Name [Tag]"
        result = self.calculate_nickname("Name", "[Tag]", ["[Tag]"])
        self.assertEqual(result, "Name [Tag]")

    def test_idempotency(self):
        # User has correct tag
        # Input: "Name [Tag]"
        # Output: "Name [Tag]"
        result = self.calculate_nickname("Name [Tag]", "[Tag]", ["[Tag]"])
        self.assertEqual(result, "Name [Tag]")

    def test_wrong_tag_removal(self):
        # User has wrong tag
        # Input: "Name [Wrong]"
        # Output: "Name [Right]"
        result = self.calculate_nickname("Name [Wrong]", "[Right]", ["[Right]", "[Wrong]"])
        self.assertEqual(result, "Name [Right]")

    def test_multiple_tags_cleanup(self):
        # User has multiple tags
        # Input: "Name [Tag1] [Tag2]"
        # Target: [Tag1]
        result = self.calculate_nickname("Name [Tag1] [Tag2]", "[Tag1]", ["[Tag1]", "[Tag2]"])
        self.assertEqual(result, "Name [Tag1]")

    def test_long_name(self):
        # Long name
        long_name = "A" * 30
        # Target: [Tag] (5 chars)
        # Result should be 32 chars max. "Name [Tag]"
        # 32 - 5 - 1 = 26 chars allowed for name.
        result = self.calculate_nickname(long_name, "[Tag]", ["[Tag]"])
        self.assertEqual(len(result), 32)
        self.assertTrue(result.endswith(" [Tag]"))
        self.assertEqual(result.split(" ")[0], "A" * 26)

    def test_no_target_tag(self):
        # No target tag, should strip known tags
        result = self.calculate_nickname("Name [Old]", None, ["[Old]"])
        self.assertEqual(result, "Name")

    def test_tag_in_middle(self):
        # Tag in middle
        result = self.calculate_nickname("Name [Tag] Surname", "[Tag]", ["[Tag]"])
        # Logic removes tag: "Name Surname"
        # Appends tag: "Name Surname [Tag]"
        self.assertEqual(result, "Name Surname [Tag]")

if __name__ == '__main__':
    unittest.main()
