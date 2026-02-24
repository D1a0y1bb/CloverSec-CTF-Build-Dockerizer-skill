// 导入依赖
const express = require('express');
const path = require('path');

// 创建 express 应用实例
const app = express();

// 端口可以从环境变量读取，便于 Docker 中配置
const port = process.env.PORT || 3000;

// 解析 JSON 请求体
app.use(express.json({ limit: '1mb' }));

// Web 应用防火墙 (WAF)：仅允许白名单字符
// 允许的字符：数字(0,1,2,3,4,5,6,7,9)、操作符(!.+-*/)、括号()[]
const ALLOW_CHARS = /^[012345679!\.\-\+\*\/\(\)\[\]]+$/;

const WAF = (recipe) => {
    if (typeof recipe !== 'string') {
        return false;
    }
    return ALLOW_CHARS.test(recipe);
};

// 计算函数：执行数学表达式计算
function calc(operator) {
    // 按题目需求保留 eval 特性
    return eval(operator);
}

// 提供静态资源目录（前端页面、提示脚本等）
const publicDir = path.join(__dirname, 'public');
app.use(express.static(publicDir));

// 根路由：返回计算器页面
app.get('/', (req, res) => {
    res.sendFile(path.join(publicDir, 'index.html'));
});

// 计算接口
app.post('/calc', (req, res) => {
    const { expr } = req.body || {};
    console.log(expr);

    // WAF 校验
    if (!WAF(expr)) {
        // 返回被 WAF 拦截标记
        return res.json({ result: 'WAF' });
    }

    try {
        const result = calc(expr);
        return res.json({ result });
    } catch (err) {
        // 对表达式错误做一个简单的兜底
        return res.status(400).json({ result: 'ERROR' });
    }
});

// 轻度“藏起来”的 WAF 提示链路：
// 1. robots.txt 暗示有一个 protocol 文件；
// 2. /protocol.js 中用字符编码的方式给出白名单信息，需要选手再处理一下。

// robots.txt：只是指向一个可疑资源，不直接给出正则
app.get('/robots.txt', (req, res) => {
    res.type('text/plain').send([
        'User-agent: *',
        'Disallow: /protocol.js',
        'Disallow: /internal-status'
    ].join('\n'));
});

// /protocol.js 实际由静态目录提供，这里不需要额外路由

// 启动服务
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});

