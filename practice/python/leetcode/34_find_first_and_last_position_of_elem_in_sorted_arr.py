class Solution:
    def searchRange(self, nums: list[int], target: int) -> list[int]:

        def search(isFirst):
            bound = -1
            l , r = 0, len(nums) -1
            while l <= r:
                mid = (l + r) // 2
                if target > nums[mid]:
                    l = mid + 1
                elif target < nums[mid] :
                    r = mid - 1
                else:
                    bound = mid
                    if isFirst:
                        r = mid - 1
                    else:
                        l = mid + 1
            return bound
        return [search(True), search(False)]
                
res = Solution().searchRange([1, 2, 2, 2, 4, 5], 2)
print(res)
