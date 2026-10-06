<?php
declare(strict_types=1);

header('Content-Type: text/plain; charset=UTF-8');

echo "RDG PHP sample is running.\n";
echo "status: baseline-fixed\n";

// RDG 防御修复样例：保留“疑似攻击输入”的入口，但明确阻断，不执行反序列化。
if (isset($_GET['p'])) {
    $payload = (string) $_GET['p'];
    if (stripos($payload, 'O:') !== false || stripos($payload, 'C:') !== false) {
        echo "serialized payload blocked\n";
    } else {
        echo "input accepted as plain text\n";
    }
}
