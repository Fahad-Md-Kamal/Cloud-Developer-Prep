class Solution:
    def mySqrt(self, x: int) -> int:
        
        if x < 2:
            return x
        
        left, right = 1, x // 2
        while left <= right:
            mid = (left + right) // 2
            square = mid * mid
            
            if square == x:
                return mid
            elif square < x:
                left = mid + 1
            else:
                right = mid - 1
        return right


if __name__ == "__main__":
    test_cases = [
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 2),
        (8, 2),
        (9, 3),
        (10, 3),
        (15, 3),
        (16, 4),
        (17, 4),
        (24, 4),
        (25, 5),
        (26, 5),
        (35, 5),
        (36, 6),
        (99, 9),
        (100, 10),
        (101, 10),
        (2147483647, 46340),
    ]

    solution = Solution()
    for i, (x, expected) in enumerate(test_cases, start=1):
        actual = solution.mySqrt(x)
        assert actual == expected, (
            f"Test {i} failed: mySqrt({x}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: mySqrt({x}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")