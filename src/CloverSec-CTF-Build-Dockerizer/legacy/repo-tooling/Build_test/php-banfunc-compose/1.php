<?php
/**
 * 简单的命令执行脚本
 * 注意：此脚本包含安全风险，仅用于学习目的
 */

// 显示当前文件的源代码
highlight_file(__FILE__);

// 获取GET参数中的cmd命令
$cmd = $_GET['cmd'];

// 定义黑名单正则表达式模式
$blacklist_pattern = '/\~|\`|\@|\#|\\$|\%|\^|\&|\*|\（|\）|\-|\=|\+|\{|\[|\]|\}|\:|\'|\"|\,|\<|\.|\>|\/|\?|\\\\|[0-9]|'
    . 'limiter|unparsed|gzhandler|quotes|ttyname|diff|decl|fileatime|type|implode|gzgetc|hexdec|strimwidth|'
    . 'encodings|function|shorthash|cfg|gmdate|fputcsv|xml|caches|sleep|finish|mlsd|peak|continue|interfaces|'
    . 'kill|register|aliases|aead|rewrite|pwhash|verify|chgrp|nanosleep|static|setgid|json|strchr|token|'
    . 'boolval|getmyinode|clearstatcache|ob|cdata|output|extract|loader|challenge|number|limit|rename|dh|'
    . 'gztell|rawlist|errors|value|uassoc|getpid|mx|modify|install|acos|strstr|digit|phpcredits|ftruncate|'
    . 'arsort|secretkey|linkinfo|tan|to|wordwrap|unshift|end|locations|from|byte|floor|secretbox|interface|'
    . 'printf|local|unregister|dir|bucket|reverse|bytes|flock|compare|getpwnam|getegid|checkdate|strrchr|'
    . 'uksort|pack|generichash|search|unpack|regenerate|html|constants|sqrt|chars|shuffle|scandir|values|'
    . 'exists|real|opendir|preg|sum|identifiers|setpgid|diskfreespace|stristr|getsid|grep|strpos|url|'
    . 'rehash|flip|full|backtrace|bin2base64|getservbyport|timezone|ed25519|language|finfo|digest|subject|'
    . 'scryptsalsa208sha256|alter|derive|timestamp|internal|ftell|max|funcs|context|regs|gzopen|uintersect|'
    . 'temp|detached|geteuid|subclass|save|keypair|levenshtein|timeout|ns|index|stripslashes|expire|drivers|'
    . 'addcslashes|rad2deg|parser|decbin|strnatcasecmp|gethostbyname|sin|meta|udiff|sent|apply|crypto|acosh|'
    . 'substr|log|ssl|fileperms|remove|dtd|options|included|call|fputs|writable|mem|splice|request|property|'
    . 'size|sprintf|in|mail|of|round|feof|realpath|seed|on|strtr|unset|localtime|strpbrk|tanh|gzcompress|'
    . 'recvfrom|strnatcmp|current|pkcs7|filemtime|struct|params|chown|graph|fstat|long2ip|sodium|traits|'
    . 'alpha|lstat|session|path|sunset|urlencode|executable|tick|indent|natsort|string|asinh|stripcslashes|'
    . 'rmdir|strripos|fastcgi|convert|pop|hebrevc|open|strtoupper|trim|sapi|magic|seal|getimagesize|sendto|'
    . 'autoload|implicit|send|ukey|history|floatval|ref|arg|quoted|format|strcspn|iptcembed|getloadavg|'
    . 'intval|uri|lower|nb|initgroups|multisort|name|mimeheader|total|phpversion|pi|list|fgetcsv|rekey|'
    . 'rawurlencode|rewind|user|getgroups|iterator|exception|octdec|ftp|bindec|quote|details|getpgid|'
    . 'strftime|pasv|strncasecmp|crc32|getmygid|into|coding|iv|init|new|closedir|fmod|deg2rad|instruction|'
    . 'quotemeta|escapeshellarg|doubleval|sub|rot13|sinh|restore|gzuncompress|log10|gzread|commit|'
    . 'gethostbynamel|mime|gmstrftime|usort|namespace|filegroup|csr|mkfifo|record|element|mberegi|len|'
    . 'disable|bin2hex|printable|lchgrp|combine|attribute|gzpassthru|gethostbyaddr|cache|settype|mbereg|'
    . 'runtime|load|xmlwriter|setegid|syslog|sun|nl2br|asort|fseek|gethostname|pos|set|getservbyname|site|'
    . 'abbr|mhash|kx|vsprintf|expm1|popen|push|eregi|umask|getpgrp|gzdecode|uses|module|repeat|close|'
    . 'connect|openssl|s2k|declared|default|isatty|float|debug|system|getallheaders|contents|chr|'
    . 'abbreviations|getprotobyname|ezmlm|ntop|fnmatch|x509|fprintf|gzeof|rsort|uname|addslashes|pk|'
    . 'getmxrr|gmmktime|func|vars|character|checkpurpose|image|getrandmax|source|handlers|auth|cert|'
    . 'extension|dirname|apache|getcsv|class|hypot|soundex|start|vprintf|first|pair|redisplay|space|array|'
    . 'build|use|cos|fscanf|block|socket|callable|getimagesizefromstring|notation|setlocale|fill|iptcparse|'
    . 'hash|word|parse|forward|get|transitions|mbregex|compact|gzgetss|flush|map|compute|sys|alloc|fgetss|'
    . 'sign|getdate|spl|usleep|length|uudecode|gzgets|put|methods|errno|uuencode|bool|lcfirst|location|'
    . 'systype|files|strrpos|key|localeconv|getrusage|prev|rtrim|pbkdf2|random|gc|tags|ftok|available|'
    . 'define|sort|scalarmult|deflate|dom|range|crypt|has|buffer|pow|regex|lock|hex2bin|match|closelog|is|'
    . 'reduce|stat|enable|setpos|resolve|sha1|assert|all|functions|gettimeofday|pull|gzclose|dechex|uasort|'
    . 'append|getgid|connection|var|classes|clean|null|gzrewind|accept|prepend|lcg|column|xchacha20poly1305|'
    . 'sunrise|detect|strcmp|select|uploaded|alnum|openlog|trigger|spki|update|strrichr|getenv|numeric|'
    . 'natcasesort|change|getgrnam|zlib|ctype|stripos|getrlimit|blocking|id|putenv|tmpfile|reporting|cycles|'
    . 'abs|getpwuid|browser|lchown|processing|constant|setcookie|print|args|alias|unserialize|sizeof|fget|'
    . 'rawurldecode|getprotobynumber|libxml|import|explode|cosh|unlink|pclose|level|privatekey|file|ucwords|'
    . 'getlogin|quit|strip|keygen|loaded|simplexml|filectime|assoc|infinite|encoding|symlink|strncmp|memcmp|'
    . 'cipher|escapeshellcmd|supports|move|http|secretstream|wrapper|htmlentities|response|make|fsockopen|'
    . 'gzwrite|export|getuid|mbsplit|money|highlight|pathinfo|ord|line|ceil|zend|filter|writeable|'
    . 'rewinddir|product|resources|split|gzencode|decode|wrappers|base64|shift|gpc|private|server|passthru|'
    . 'curve|and|krsort|handler|isodate|pdo|ietf|atan|gzputs|ireplace|ltrim|flags|atanh|touch|hebrev|punct|'
    . 'include|vfprintf|status|fread|memzero|utf8|header|gzseek|similar|keys|unpad|external|immutable|log1p|'
    . 'filetype|order|char|called|metaphone|seteuid|rand|final|intdiv|times|strerror|strlen|xdigit|show|'
    . 'slice|getpos|atan2|serialize|pkcs12|mktime|getcwd|readfile|cntrl|setsid|nl|copy|hmac|pad|posix|cyr|'
    . 'disk|strtok|merge|info|pseudo|time|readgzfile|htmlspecialchars|nice|fgets|entity|comment|ini|'
    . 'implements|getmyuid|algos|ignore|readlink|md|memory|getopt|method|login|fwrite|until|aborted|fopen|'
    . 'preferred|intersect|gzinflate|mkdir|error|defined|fclose|strtotime|tempnam|next|strspn|callback|'
    . 'variables|scrub|date|mb|public|input|ctermid|reset|strcasecmp|fingerprint|hrtime|usage|whitespace|'
    . 'msg|content|getgrgid|needs|ip2long|decrypt|cookie|xor|strcoll|langinfo|publickey|decoct|setrawcookie|'
    . 'srand|strwidth|enabled|free|check|checkdnsrr|stream|getregs|strval|fpm|kdf|pkey|chmod|nan|min|'
    . 'required|shutdown|names|fpassthru|case|chacha20poly1305|setrlimit|scalar|filesize|nlist|collect|'
    . 'equals|aes256gcm|exec|upper|shell|urldecode|getmypid|delete|chunk|fgetc|mt|gzdeflate|strptime|'
    . 'terminate|fileinode|read|encode|count|scanned|option|ucfirst|exp|clear|version|num|microtime|replace|'
    . 'streams|data|sk|dump|create|walk|increment|readable|readdir|numericentity|document|text|gettype|'
    . 'sscanf|getppid|fileowner|object|link|str|double|trait|long|encrypt|query|destroy|kana|int|filters|'
    . 'recursive|each|mdtm|fflush|chdir|finite|dns|extensions|mknod|headers|strtolower|join|proc|cdup|base|'
    . 'pfsockopen|base642bin|raw|setuid|md5|php|attlist|curve25519|parents|abort|getlastmod|uniqid|table|'
    . 'asin|interval|iconv|fput|substitute|last|pton|password|pwd|inet|countable|translation|client|'
    . 'transports|readline|strrev|glob|resource|zval|integer|parent|strcut|ereg|box|idate|inflate|chop|'
    . 'unique|gzfile|iterable|net|add|code|hkdf|write|ksort|completion|offset|access/i';

// 检查命令是否匹配黑名单
if (!preg_match($blacklist_pattern, $cmd)) {
    // 如果不匹配黑名单，执行命令
    eval($cmd);
} else {
    // 如果匹配黑名单，输出警告信息
    echo "hacker!";
}

// 输出结果
echo "hacker!";