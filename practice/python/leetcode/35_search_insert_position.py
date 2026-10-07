class Solution:
    def searchInsert(self, nums: list[int], target: int) -> int:
        l, r = 0, len(nums) - 1
        while l<=r:
            mid = (l+ r)// 2
            if nums[mid] == target:
                return mid
            elif target > nums[mid]:
                l = mid + 1
            else:
                r = mid - 1
        return l


if __name__ == "__main__":
    test_cases = [
        ([1, 3, 5, 6], 5, 2),
        ([1, 3, 5, 6], 2, 1),
        ([1, 3, 5, 6], 7, 4),
        ([1, 3, 5, 6], 0, 0),
        ([1], 1, 0),
        ([1], 0, 0),
        ([1], 2, 1),
        ([1, 3], 1, 0),
        ([1, 3], 2, 1),
        ([1, 3], 3, 1),
        ([1, 3], 4, 2),
        ([1, 3], 0, 0),
        ([2, 4, 6, 8, 10], 6, 2),
        ([2, 4, 6, 8, 10], 5, 2),
        ([2, 4, 6, 8, 10], 1, 0),
        ([2, 4, 6, 8, 10], 11, 5),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 7, 6),
        ([-5, -3, -1, 0, 2, 4], -2, 2),
        ([-5, -3, -1, 0, 2, 4], 4, 5),
        ([-5, -3, -1, 0, 2, 4], -10, 0),
    ]

    solution = Solution()
    for i, (nums, target, expected) in enumerate(test_cases, start=1):
        actual = solution.searchInsert(nums, target)
        assert actual == expected, (
            f"Test {i} failed: searchInsert({nums!r}, {target}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: searchInsert({nums!r}, {target}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
