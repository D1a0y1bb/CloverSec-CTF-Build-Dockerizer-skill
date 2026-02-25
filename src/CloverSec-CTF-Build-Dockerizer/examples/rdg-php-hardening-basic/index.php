<?php
highlight_file(__FILE__);

// RDG 样例：保留一个最小 PHP 审计入口，便于验证模板兼容性。
if (isset($_GET['data'])) {
    @unserialize($_GET['data']);
}

echo "\nRDG PHP sample is running.";
