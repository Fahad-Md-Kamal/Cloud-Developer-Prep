class Solution:
    def maxArea(self, height: list[int]) -> int:
        
        maxArea = 0
        lp, rp = 0, len(height) - 1
        
        while lp < rp:
            minH = min(height[lp], height[rp])
            area = minH * (rp - lp)
            maxArea = max(maxArea, area)
            if lp < rp:
                lp += 1
            else:
                rp += 1
        return maxArea

ins = Solution()
res = ins.maxArea([1,8,6,2,5,4,8,3,7])
print(res)
