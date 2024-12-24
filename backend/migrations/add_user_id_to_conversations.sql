-- 添加用户ID字段到conversations表
ALTER TABLE conversations 
ADD COLUMN user_id INTEGER REFERENCES users(id);

-- 更新现有记录（可选）
UPDATE conversations 
SET user_id = (SELECT id FROM users WHERE is_admin = true LIMIT 1)
WHERE user_id IS NULL;

-- 设置非空约束
ALTER TABLE conversations 
ALTER COLUMN user_id SET NOT NULL;