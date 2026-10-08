class Solution:
    
    def isNumChar(self, c):
        return (
            (ord("A") <= ord(c) <= ord("Z")) or 
            (ord("a") <= ord(c) <= ord("z")) or 
            (ord("0") <= ord(c) <= ord("9"))
            )
        
    def isPalindrome(self, s: str) -> bool:
        lp, rp = 0, len(s) - 1
        
        while lp < rp:
            if not self.isNumChar(s[lp]):
                lp += 1
            elif not self.isNumChar(s[rp]):
                rp -= 1
            else:
                if s[lp].lower() != s[rp].lower():
                    return False
                lp += 1
                rp -= 1
        return True


if __name__ == "__main__":
    test_cases = [
        ("A man, a plan, a canal: Panama", True),
        ("race a car", False),
        (" ", True),
        ("a", True),
        (".,", True),
        ("0P", False),
        ("ab_a", True),
        ("Was it a car or a cat I saw?", True),
        ("Madam, in Eden, I'm Adam", True),
        ("No lemon, no melon", True),
        ("12321", True),
        ("12345", False),
        ("1a2", False),
        ("Able was I ere I saw Elba", True),
        ("Never odd or even", True),
        ("Eva, can I see bees in a cave?", True),
        ("Step on no pets", True),
        ("Hello, World!", False),
        ("!!!", True),
        ("a.", True),
    ]

    solution = Solution()
    for i, (s, expected) in enumerate(test_cases, start=1):
        actual = solution.isPalindrome(s)
        assert actual == expected, (
            f"Test {i} failed: isPalindrome({s!r}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: isPalindrome({s!r}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")