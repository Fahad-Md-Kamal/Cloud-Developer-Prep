class Solution:
    def climbStairs(self, n: int) -> int:
        a, b = 1, 1
        for _ in range(n-1):
            tmp = a
            a = a + b
            b = tmp
        return a


if __name__ == "__main__":
    test_cases = [
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 5),
        (5, 8),
        (6, 13),
        (7, 21),
        (8, 34),
        (9, 55),
        (10, 89),
        (11, 144),
        (12, 233),
        (13, 377),
        (14, 610),
        (15, 987),
        (16, 1597),
        (20, 10946),
        (30, 1346269),
        (38, 63245986),
        (45, 1836311903),
    ]

    solution = Solution()
    for i, (n, expected) in enumerate(test_cases, start=1):
        actual = solution.climbStairs(n)
        assert actual == expected, (
            f"Test {i} failed: climbStairs({n}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: climbStairs({n}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
