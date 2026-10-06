class Solution:
    def removeElement(self, nums: list[int], val: int) -> int:
        cp = 0
        for i in range(len(nums)):
            if nums[i] != val:
                nums[cp] = nums[i]
                cp += 1
        return cp