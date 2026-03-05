-- check_and_add.lua
-- 原子操作：去重检查 + 入队 + 设置 TTL
--
-- KEYS[1]: bloom filter key (e.g. "bf:spider_name")
-- KEYS[2]: zset queue key  (e.g. "queue:spider_name")
-- ARGV[1]: url fingerprint
-- ARGV[2]: priority score
-- ARGV[3]: seed json string
-- ARGV[4]: ttl seconds (0 = no expiry)
--
-- 返回: 1 = 新增成功, 0 = 已存在

local exists = redis.call('BF.EXISTS', KEYS[1], ARGV[1])
if exists == 1 then
    return 0
end

redis.call('BF.ADD', KEYS[1], ARGV[1])
redis.call('ZADD', KEYS[2], ARGV[2], ARGV[3])

if tonumber(ARGV[4]) > 0 then
    redis.call('EXPIRE', KEYS[2], ARGV[4])
end

return 1
