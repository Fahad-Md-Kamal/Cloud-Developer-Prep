class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        tmpDict = dict()
        for i in range(len(nums)):
            comp = target - nums[i]
            if comp in tmpDict:
                return [tmpDict[comp], i]
            tmpDict[nums[i]] = i
        return [-1, -1]


ins = Solution()
res = ins.twoSum([2, 7, 11, 15], 9)
print(res)
