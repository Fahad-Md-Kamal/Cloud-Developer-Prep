class Solution:
    def sortColors(self, nums: list[int]) -> None:
        l, r = 0, len(nums) - 1
        i = 0
        
        def swap(a, b):
            tmp = nums[a]
            nums[a] = nums[b]
            nums[b] = tmp
        
        while i <= r:
            if nums[i] == 0:
                swap(l, i)
                l += 1
            elif nums[i] == 2:
                swap(i, r)
                r -= 1
                i -= 1
            i += 1


if __name__ == "__main__":
    test_cases = [
        ([2, 0, 2, 1, 1, 0], [0, 0, 1, 1, 2, 2]),
        ([2, 0, 1], [0, 1, 2]),
        ([0], [0]),
        ([1], [1]),
        ([2], [2]),
        ([0, 0, 0], [0, 0, 0]),
        ([1, 1, 1], [1, 1, 1]),
        ([2, 2, 2], [2, 2, 2]),
        ([0, 1, 2], [0, 1, 2]),
        ([2, 1, 0], [0, 1, 2]),
        ([1, 0], [0, 1]),
        ([0, 1], [0, 1]),
        ([1, 2], [1, 2]),
        ([2, 1], [1, 2]),
        ([0, 2], [0, 2]),
        ([2, 0], [0, 2]),
        ([1, 2, 0, 2, 1, 0, 0, 1, 2], [0, 0, 0, 1, 1, 1, 2, 2, 2]),
        ([0, 0, 1, 1, 2, 2], [0, 0, 1, 1, 2, 2]),
        ([2, 2, 1, 1, 0, 0], [0, 0, 1, 1, 2, 2]),
        ([1, 0, 2, 1, 0, 2, 1, 0, 2], [0, 0, 0, 1, 1, 1, 2, 2, 2]),
    ]

    solution = Solution()
    for i, (nums, expected) in enumerate(test_cases, start=1):
        arr = nums.copy()
        solution.sortColors(arr)
        assert arr == expected, (
            f"Test {i} failed: sortColors({nums!r}) -> {arr}, expected {expected}"
        )
        print(f"Test {i:2d} passed: sortColors({nums!r}) -> {arr}")

    print(f"\nAll {len(test_cases)} test cases passed!")
