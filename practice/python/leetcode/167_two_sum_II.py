class Solution:
    def twoSum(self, numbers: list[int], target: int) -> list[int]:
        
        lp, rp = 0, len(numbers) - 1
        
        while lp < rp:
            comp = numbers[lp] + numbers[rp]
            if comp == target:
                return [lp + 1, rp + 1]
            elif comp > target:
                rp -= 1
            else:
                lp += 1
        return [-1, -1]


if __name__ == "__main__":
    test_cases = [
        ([2, 7, 11, 15], 9, [1, 2]),
        ([2, 3, 4], 6, [1, 3]),
        ([-1, 0], -1, [1, 2]),
        ([1, 2, 3, 4, 5], 9, [4, 5]),
        ([1, 2, 3, 4, 5], 3, [1, 2]),
        ([-3, -1, 0, 2, 4, 6], 1, [1, 5]),
        ([0, 0, 3, 4], 0, [1, 2]),
        ([5, 25, 75], 100, [2, 3]),
        ([1, 3, 4, 5, 7, 10, 11], 9, [3, 4]),
        ([-10, -5, -2, 0, 3, 8], -2, [1, 6]),
        ([1, 2], 3, [1, 2]),
        ([2, 2, 2, 2], 4, [1, 4]),
        ([-5, -3, -2, -1], -8, [1, 2]),
        ([1, 2, 3, 4, 4, 9, 56, 90], 8, [4, 5]),
        ([3, 24, 50, 79, 88, 150, 345], 200, [3, 6]),
        ([-2, 1, 2, 4, 7, 11], 0, [1, 3]),
        ([1, 5, 8, 11, 15, 20, 25, 30], 36, [4, 7]),
        ([-100, -50, 0, 50, 100], 0, [1, 5]),
        ([2, 3, 5, 8, 11, 15], 20, [3, 6]),
        ([10, 20, 30, 40, 50], 90, [4, 5]),
    ]

    solution = Solution()
    for i, (numbers, target, expected) in enumerate(test_cases, start=1):
        actual = solution.twoSum(numbers, target)
        assert actual == expected, (
            f"Test {i} failed: twoSum({numbers!r}, {target}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: twoSum({numbers!r}, {target}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
