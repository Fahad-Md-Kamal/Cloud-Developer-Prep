class Solution:
    def maxProduct(self, nums: list[int]) -> int:
        res = max(nums)
        curr_max = curr_min = 1
        
        for n in nums:
            tmp = curr_max * n
            curr_max = max(tmp, curr_min * n, n)
            curr_min = min(tmp, curr_min * n, n)
            
            res = max(curr_max, curr_min, res)
        return res


if __name__ == "__main__":
    test_cases = [
        ([2, 3, -2, 4], 6),
        ([-2, 0, -1], 0),
        ([-2, 3, -4], 24),
        ([0, 2], 2),
        ([-1], -1),
        ([2], 2),
        ([-2, -3, -4], 12),
        ([0, 0, 0], 0),
        ([1, 0, -1, 2, 3, -5, -2], 60),
        ([2, -5, -2, -4, 3], 24),
        ([-4, -3, -2], 12),
        ([3, -1, 4], 4),
        ([-1, -2, -9, -6], 108),
        ([0, -3, 1, 1], 1),
        ([-2, -3, 0, -2, -40], 80),
        ([5, 6, -3, 4, -3], 1080),
        ([1, 2, 3], 6),
        ([-1, 0, 1], 1),
        ([6, -3, -10, 0, 2], 180),
        ([-2, -1], 2),
    ]

    solution = Solution()
    for i, (nums, expected) in enumerate(test_cases, start=1):
        actual = solution.maxProduct(nums)
        assert actual == expected, (
            f"Test {i} failed: maxProduct({nums!r}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: maxProduct({nums!r}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
