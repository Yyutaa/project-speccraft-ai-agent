# 超大 Excel 订单异步导入：依赖业务口径

[actor] 订单运营人员发起导入。
[flow] 上传后异步处理订单行。
[permission] 订单运营角色可操作。
[failure] 重复文件需要按“业务订单唯一键”去重。
[acceptance] 同一订单不会重复创建。

“业务订单唯一键”的组成字段只存在于授权业务知识库。本 Fixture 预期在 Provider 不可用时返回
`NEED_USER_INPUT / KNOWLEDGE_REQUIRED_UNAVAILABLE`，不得由模型猜测字段。
