class Solution:
    def longestCommonPrefix(self, strs: list[str]) -> str:
        res = ""
        for i in range(len(strs[0])):
            for s in strs:
                if i == len(s) or s[i] != strs[0][i]:
                    return res
            res += strs[0][i]
        return res

ins = Solution()
res = ins.longestCommonPrefix(["flow", "flower", "flight"])
print(res)
