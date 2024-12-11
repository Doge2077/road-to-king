# 缓存发展史

****

## 缓存经典场景

****

![image-20240108192947119](https://image.itbaima.net/images/40/image-2024010819312618.png)

在没有引入缓存前，为了应对大量流量，一般采用：

- LVS 代理
- Nginx 做负载均衡
- 搭建 Tomcat 集群

这种方式下，随着访问量的增大，响应力越差，逐渐无法满足用户体验。

在引入缓存后：

![image-20240108193930755](https://image.itbaima.net/images/40/image-20240108192027523.png)

****

### 三大经典缓存读写策略

****

旁路缓存模式：Cache Aside Pattern

- 写：先更新`DB`，然后直接删除 `cache`
- 读：从 `cache` 中读取数据，读取到直接返回，否则查 `DB` 后返回，然后将查到的数据写入 `cache`

读写穿透模式：Read/Write Through Pattern

- 写：先查 `cache`，`cache` 中不存在，直接更新 `DB`，否则先更新 `cache`，然后 `cache` 服务更新 `DB`
- 读：从 `cache` 中读取数据，读取到直接返回，否则查 `DB` 后写入到 `cache`，之后返回数据

异步缓存写入：Write Behind Pattern

- 写：写入只更新 `cache`，然后异步批量更新 `DB`
- 读：从 `cache` 中读取数据，读取到直接返回，否则查 `DB` 后写入到 `cache`，之后返回数据

****

### 双写一致性解决方案

****

以上三种经典的读写策略在一定条件下都会产生缓存和数据库数据不一致的问题，这里给出两种解决方案

**同步方案**：

- 延迟双删：更新数据时先删除缓存，然后修改数据库，延迟一段时间后再次删除缓存
- 延迟一段时间是为了保证数据库集群下的数据同步

**异步方案**：

- 使用消息队列：更改代码加入异步操作缓存的逻辑代码，数据库操作完毕后将要同步的数据发给 mq，mq 的消费者从 mq 获取数据更新缓存
- 使用 canal 组件实现同步：不需要更改业务代码，只需要部署一个 canal 服务，canal 把自己伪装为了 mysql 的从节点，canal 读取 binlog 日志更新缓存

****

## 分布式缓存方案选型

****

分布式缓存主要解决的是单机缓存的容量受服务器限制并且无法保存通用的信息。

因为，本地缓存只在当前服务里有效，部署两个相同的服务，他们两者之间的本地缓存数据无法共通。

常见的分布式缓存方案为：

- Redis
- Memcache
- Tair

****

### Redis 和 Memcache 对比

****

**共同点**：

- 都是基于内存的数据库，一般都用来当做缓存使用
- 都有过期策略

**区别**：

- Redis 支持的数据类型更丰富，而 Memcached 只支持最简单的 key-value 数据类型
- Redis 支持数据持久化，有 RDB 和 AOF 两种方案，而 Memcached 没有持久化功能，数据全部存在内存之中
- Redis 原生支持集群模式，Memcached 没有原生的集群模式，需要依靠客户端来实现往集群中分片写入数据
- Redis 支持发布订阅模型、LUA  脚本、事务等功能，而 Memcached 不支持

****

### Redis 和 Tair 对比

****

**共同点**：

- 都支持数据持久化
- 都有过期策略
- 都支持分布式存储

**区别**：

- Redis 开发语言为 C，Tair 是 C++，
- Redis 支持的数据类型更丰富，而 Tair 主要支持字符串和列表
- Redis 利用主从赋值进行数据备份和同步 ，而 Tair 配置了复制因子的多副本机制，保证数据的可靠性
- 对于数据量大的场景下，Tair 更适用

推荐阅读：[技术选型系列 - Tair&Redis对比](https://cloud.tencent.com/developer/article/1371099)

****

# Redis 数据类型

****

## Redis 的 key 设计规范

****

Redis 常见的数据类型：字符串（String），哈希（Hash），列表（List），集合（Set），有序集合（Zset）

![image-20240108224119079](https://image.itbaima.net/images/40/image-20240108229766334.png)

对于 Key 的设计，一般遵循如下规范：

- 可读性：一般以业务名（数据库名）为前缀，用冒号分割，例如：`数据库名:业务名:表名id`
- 简洁性：保证可读性的前提下，Key 的长度越短越好，原则上每个 Key 不能超过 44 字节，不能包含特殊字符（空格、换行、转义）
- 避免 BigKey：
  - 情况一：键值对的值本身就很大，如 value 为 1 MB 的 string 类型，在业务层尽量将 string 大小控制在 10 KB 以下
  - 情况二：键值对的值是集合类型，集合元素个数非常多，此时尽量把集合类型的元素个数控制在 1 万以下
- 针对高频 Key 进行设计：一般只将热点数据的 Key 考虑加入 Redis，如即时排行榜、直播信息等

****

## String 类型

****

### 基础概念

****

String 的底层结构是，简单动态字符串（Simple Dynamic String,SDS），特点：

- SDS 不仅可以保存文本数据，还可以保存二进制数据
- SDS 获取字符串长度的时间复杂度是 O(1)
- Redis 的 SDS API 是安全的，拼接字符串不会造成缓冲区溢出

在保存数字、小字符串时因为采用 INT 和 EMBSTR 编码，内存结构紧凑，只需要申请一次内存分配，效率更高，更节省内存。

对于超过44字节的大字符串时则需要采用 RAW 编码，申请额外的 SDS 空间，需要两次内存分配，效率较低，内存占用也较高，但大小不超过 512 MB，因此建议单个 value 尽量不要超过 44 字节。

****

### 扩展操作

****

缓存对象：

- `set key value` 单值缓存

针对数值进行操作：

- ```shell
  # 设置数值数据增加指定范围的值
  incr key
  incrby key increment
  incrbyfloat key increment
  ```

- ```shell
  # 设置数值数据减少指定范围的值
  decr key
  decrby key increment
  ```

- ```shell
  # 设置数据具有指定的生命周期
  setex key seconds value
  psetex key milliseconds value
  ```

分布式锁：`setnx key:xxx true` 设置分布式锁，用于请求限流 

**注意**：

- string 在 redis 内部存储默认就是一个字符串，当遇到增减类操作 `incr`，`decr` 时会转成数值型进行计算
- 按数值进行操作的数据，如果原始数据不能转成数值，或超越了redis 数值上限范围，将报错 9223372036854775807（java中Long型数据最大值，`Long.MAX_VALUE`）

****

### 应用场景

****

主页高频访问信息显示控制，例如：新浪微博大 V 主页显示粉丝数与微博数量，需要针对这些高频访问的信息进行缓存处理

**解决方案**：

- 在 Redis 中为大 V 用户设定用户信息，以用户主键和属性值作为 Key，后台设定定时刷新策略即可

- ```shell
  user:id:3506728370:fans 114514
  user:id:3506728370:blogs 1919
  user:id:3506728370:focuses 810
  ```

- 使用 json 格式保存数据

- ```shell
  user:id:3506728370 {"fans":12210947, "blogs":6164, "focuses":83 }
  ```

****

## Hash 类型

****

### 基础概念

****

与 Java 中的 HashMap 类似，但底层结构是压缩列表和哈希表，特点：

- 如果哈希类型元素个数小于 512（可设置 hash-max-ziplist-entries 修改），所有值小于 64 字节（可设置 hash-max-ziplist-value 修改），则会使用压缩列表作为底层数据结构
- 不满足上述条件则会使用哈希表作为数据结构

存储形式为：`key-value`，其中 `value=[{field1, value1}, {field2, value2}, {field3, value3}]`，如下图所示：

![image-20240108234005984](https://image.itbaima.net/images/40/image-20240108234848886.png)

与 Java 中的 HashMap 不同的是，Redis 中的 Hash 底层采用了渐进式 rehash 的算法，在做 rehash 时会创建一个新的 HashTable，每次操作元素时移动一部分数据，直到所有数据迁移完成，再用新的 HashTable 来代替旧的，避免了因为 rehash 导致的阻塞，因此性能更高。

在 Redis 7.0 中，压缩列表数据结构已经废弃了，交由 listpack 数据结构来实现了：

- `Listpack` 的内部结构通常由一个连续的字节数组组成，其中包含了列表的元素和元数据
- 支持一范围查询、索引和迭代，适用于需要频繁地进行插入、删除和访问的场景

****

### 扩展操作

****

对象缓存：

- `HMSET user {userId}:username zhangfei {userId}:password 123456` 
- `HMSET user 1:username zhangfei 1:password 123456` 
- `HMGET user 1:username 1:password`

针对数值进行操作：

- ```shell
  # 设置指定字段的数值数据增加指定范围的值
  hincrby key field increment
  hincrbyfloat key field increment
  ```

**注意**：

- Hash 类型中 value 只能存储字符串，不允许存储其他数据类型，不存在嵌套现象。如果数据未获取到，对应的值为 `nil`
- 每个 Hash 可以存储 $2^{32}-1$ 个键值对，但不可以将 Hash 作为对象列表使用
- Hgetall 操作可以获取全部属性，如果内部 field 过多，遍历整体数据效率就很会低，有可能成为数据访问瓶颈

****

### 应用场景

****

双十一期间，电商平台用户购物车信息存储，用户会对购物车信息进行频繁访问和修改

**解决方案**：

购物车信息存储：

- 以用户 id 作为 Key
- value 形式为 `{field1, value1}`，其中 `field1` 商品 `id`，`value1` 为数量，也可以选择型将价格、活动信息添加

购物车操作：

- 添加商品：`HSET cart:{userId} {商品Id} 1`
- 添加数量：`HINCRBY cart{userId} {商品Id} 1`
- 商品总数：`HLEN cart:{userId}`
- 删除商品：`HDEL cart:{userId} {商品Id}`
- 获取购物车内所有商品：`HGETALL cart:{userId}`

当前仅仅是将商品 `id` 存储到了 Redis 中，在回显商品具体信息的时候，还需要拿着商品 `id` 查询一次数据库，获取完整的商品的信息

****

## List 类型

****

### 基础概念

****

List 其实就是链表，只不过在 Redis 的实现中是双向的，如图所示：

![image-20240109224232863](https://image.itbaima.net/images/40/image-2024010922792485.png)

3.2 之前的版本 List 底层由由双向链表和压缩列表实现，特点：

- 如果列表元素个数小于 512（可设置 list-max-ziplist-entries 修改），所有值小于 64 字节（可设置 list-max-ziplist-value 修改），则会使用压缩列表作为底层数据结构
- 不满足上述条件则会使用双向链表作为数据结构

3.2 之后的版本，底层仍采用了 ZipList（压缩列表）来做基础存储。当压缩列表数据达到阈值则会创建新的压缩列表。每个压缩列表作为一个双端链表的一个节点， 终形成一个 QuickList 结构。

**QuickList**：

- 内部结构由多个 `ziplist` 组成，其中每个 `ziplist` 都是一个紧凑的压缩列表（compressed list），用于存储有序列表的元素。每个 `ziplist` 都包含多个节点，每个节点都可以存储一个元素。
- 使用分层的结构来加速范围查询操作。每个 `ziplist` 都有一个 level 属性，表示该 `ziplist` 中节点的高度。通过在不同层级的 `ziplist` 上进行跳跃，可以快速定位到目标范围的起始位置，并进行后续的线性搜索。

****

### 扩展操作

****

移除指定数据：

- ```shell
  lrem key count value
  ```

规定时间内获取并移除数据：

- ```shell
  blpop key1 [key2] timeout
  brpop key1 [key2] timeout
  brpoplpush source destination timeout
  ```

**注意**：

- List 中保存的数据都是 string 类型的，数据总容量是有限的，最多 $2^{32}-1$ 个元素
- List 具有索引的概念，但是操作数据时通常以队列的形式进行入队出队操作，或以栈的形式进行入栈出栈操作
- 获取全部数据操作结束索引设置为 -1
- List 可以对数据进行分页操作，通常第一页的信息来自于 List，第 2 页及更多的信息通过数据库的形式加载

****

### 应用场景

****

微信公众号发布文章或视频平台关注的博主发动态，在关注列表里面，这些消息要求按照时间进行推送

**解决方案**：

- 将订阅号消息放入用户关注列表 List 中
- 对于消息按照 `LPUSH` 或 `RPUSH` 的方式压入队列中
- 如，订阅号发布消息：`LPUSH msg:{userId} xxx`
- 查看最新消息：`LRANGE msg:{userId} 0 4`

****

## Set 类型

****

### 基础概念

****

Set 类型的底层数据结构是由**哈希表或整数集合**实现的：

- 如果集合中的元素都是整数且元素个数小于 512 （默认值，set-maxintset-entries配置）个，Redis 会使用 IntSet 作为 Set 类型的底层数据结构；
- 如果集合中的元素不满足上面条件，则 Redis 使用 hash 作为 Set 类型的底层数据结构
- Redis提供了求交集、并集等命令

Set 与 Hash 存储结构完全相同，但 Set 仅存储键，不存储值（nil），并且值是不允许重复的

****

### 扩展操作

****

Set 最具特色的就是集合运算：

![image-20240109233158298](https://image.itbaima.net/images/40/image-20240109239923929.png)

求两个集合的交、并、差集：

- ```shell
  sinter key1 [key2 ...]
  sunion key1 [key2 ...]
  sdiff key1 [key2 ...]
  ```

求两个集合的交、并、差集并存储到指定集合中：

- ```shell
  sinterstore destination key1 [key2 ...]
  sunionstore destination key1 [key2 ...]
  sdiffstore destination key1 [key2 ...]
  ```

将指定数据从原始集合中移动到目标集合中：

- ```shell
  smove source destination member
  ```

在需要获取用户共同关注的场景下，利用 Set 的集合运算再合适不过了

****

### 应用场景

****

咨询和论坛交流类网站通常针对用户有严格的约束，因此有对黑名单和白名单功能的需求

**解决方案**：

- 基于经营战略设定问题用户发现、鉴别规则
- 周期性更新满足规则的用户黑名单，加入 Set 集合
- 用户行为信息达到后与黑名单进行比对，确认行为去向
- 黑名单过滤 IP 地址：应用于开放游客访问权限的信息源
- 黑名单过滤设备信息：应用于限定访问设备的信息源
- 黑名单过滤用户：应用于基于访问权限的信息源

****

对于某个平台需要举办抽奖活动，保证参与的账号唯一且不能重复中奖

**解决方案**：

- 将某个用户加入待抽奖集合：`SADD key {userId}`
- 抽取 n 名中奖者；`SRANDMEMBER key [n] / SPOP key [n]`

****

## SortedSet 类型

****

### 基础概念

****

SortedSet，也叫 ZSet：

- 其 value 就是一个有序的 Set 集合，元素唯一，并且会按照一个指定的 score 值排序。
- SortedSet 底层的利用 Hash 表保证元素的唯一性。
- 利用跳表（SkipList）来保证元素的有序性，因此数据会有重复存储，内存占用较高，是一种典型的以空间换时间的设计。
- 不建议在SortedSet中放入过多数据。

对于跳表（SkipList）首先是链表，但与传统的链表相比有几点差异：

- 跳表结合了链表和二分查找的思想
- 元素按照升序排列存储
- 节点可能包含多个指针，指针跨度不同
- 查找时从顶层向下，不断缩小搜索范围
- 整个查询的复杂度为 O ( log n） 

****

### 应用场景

****

微博热搜排行榜、直播打赏排行榜、视频热门排行

**解决方案**：

- 维护一个排行榜的集合
- 点击对应条目，集合对应 Key 分值增加：`ZINCRBY hot:news 1 title1`
- 展示排行前 n：`ZREVRANGE hot:news 0 9 WITHSCORES`

****

## Stream 类型

****

### 基础概念

****

Redis Stream 是 Redis 5.0 版本新增加的数据结构。

Redis Stream 主要用于消息队列（MQ，Message Queue），Redis 本身是有一个 Redis 发布订阅 (pub/sub) 来实现消息队列的功能，但它有个缺点就是消息无法持久化，如果出现网络断开、Redis 宕机等，消息就会被丢弃。

简单来说发布订阅 (pub/sub) 可以分发消息，但无法记录历史消息。

而 Redis Stream 提供了消息的持久化和主备复制功能，可以让任何客户端访问任何时刻的数据，并且能记住每一个客户端的访问位置，还能保证消息不丢失。

Redis Stream 的结构如下所示，它有一个消息链表，将所有加入的消息都串起来，每个消息都有一个唯一的 ID 和对应的内容：

![image-20240320182602125](https://image.itbaima.cn/images/40/image-20240320183267220.png)

**消息队列相关命令：**

- `XADD`： 添加消息到末尾
- `XTRIM`： 对流进行修剪，限制长度
- `XDEL`： 删除消息
- `XLEN`： 获取流包含的元素数量，即消息长度
- `XRANGE`： 获取消息列表，会自动过滤已经删除的消息
- `XREVRANGE`： 反向获取消息列表，ID 从大到小
- `XREAD`： 以阻塞或非阻塞方式获取消息列表

**消费者组相关命令：**

- `XGROUP CREATE`： 创建消费者组
- `XREADGROUP GROUP`： 读取消费者组中的消息
- `XACK`： 将消息标记为"已处理"
- `XGROUP SETID`： 为消费者组设置新的最后递送消息ID
- `XGROUP DELCONSUMER`： 删除消费者
- `XGROUP DESTROY`： 删除消费者组
- `XPENDING`： 显示待处理消息的相关信息
- `XCLAIM`： 转移消息的归属权
- `XINFO`： 查看流和消费者组的相关信息；
- `XINFO GROUPS`： 打印消费者组的信息；
- `XINFO STREAM`： 打印流信息

****

### 应用场景

****

项目中部分 web 请求的处理是异步处理，web 服务调用底层模块异步执行。当底层模块处理完成后需要保存结果并通知 web 服务，所以使用 Stream 作为保存的载体，作为轻量化的一个消息队列来使用

![image-20240320182941963](https://image.itbaima.cn/images/40/image-20240320189632673.png)

****

## BitMap 类型

****

### 基础概念

****

BitMap 即位图，是一串连续的二进制数组

- 可以通过偏移量 offset 定位元素。
- BitMap 通过最小的单位 bit 来边行 01 的设置，表示某个元素的值或者状态，时间复杂度为 $\mathcal{O}(1)$。
- 由于 bit 是计算机中最小的单位，使用它进行储存将非常节省空间，特别适合一些数据量大且使用二值统计的场景

BitMap 内部存储形式如图：

![image-20240110101942852](https://image.itbaima.net/images/40/image-2024011010660663.png)

**存储对比**：

- 场景：有 1 亿用户，日均 5 千万登陆用户，要求统计每日用户的登录信息
- 如果是 Set 记录用户 ID（通常为长整型），那么每一个用户都需要 32 bit 的空间来存储
- 如果是 BitMap，则只需要 1 bit 空间来表示用户是否登录即可

**基础操作**：

- `SETBIT`：为位数组指定偏移量上的二进制位设置值，偏移量从 0 开始计数，二进制位的值只能为 0 或 1。返回原位置值。
- `GETBIT`：获取指定偏移量上二进制位的值。
- `BITCOUNT`：统计位数组中值为 1 的二进制位数量。
- `BITOP`：对多个位数组进行按位与、或、异或运算。

****

### 应用场景

****

签到统计，统计登录用户

**解决方案**：

- 签到统计时，每个用户一天的签到用 1 个 bit 位就能表示，一个月的签到情况最多用 31 个 bit 位
- 签到操作：`SETBIT uid:online:202403 15 1` 设置 uid 的用户在 2024 年 3 月的 16 日进行了签到
- 检查某天是否签到：`GETBIT uid:oneline:202403 15` 返回 1 说明 uid 用户在 2024 年 3 月的 16 日进行了签到
- 统计某月签到次数：`BITCOUNT uid:oneline:202303` 

****

## Geo 地理位置类型

****

### 基础概念

****

Redis3.2 中增加了对 GEO 类型的支持。GEO，Geographic，地理信息的缩写

- 该类型，就是元素的二维坐标，在地图上就是经纬度
- redis基于该类型，提供了经纬度设置，查询，范围查询，距离查询，经纬度Hash等常见操作

**基础操作**：

- 添加位置信息
  - 添加某个位置的经纬度信息到指定集合中： `GEOADD location-set longitude latitude name [longitude latitude name...]`
- 获取位置坐标：
  - 根据输入的位置名称和集合获取坐标：`GEOPOS location-set name [name ...]`
- 计算两个位置之间的距离：
  - 在某个集合中获取其中两个位置的直线距离：`GEODIST location-set location-x location-y [unit]`
  - 其中 `unit` 可选参数为 `m | km | mi | ft` 分别代表返回值的单位为米、千米、英里、英尺，不添加则默认单位为米
  - 例如，计算武汉到宜昌的距离：`GEODIST hubeiCities wuhan yichang`
- 指定经纬度坐标范围查询位置信息：
  - 命令：`GEORADIUS location-set longitude latitude radius m|km|ft|mi [WITHCOORD] [WITHDIST] [ASC|DESC] [COUNT count]`
  - `radius` 半径大小，可选单位米、千米、英里、英尺
  - `WITHCOORD`：可选参数，添加则在返回匹配的位置时会将该位置的经纬度一并返回
  - `WITHDIST`：可选参数，添加则在返回匹配的位置时会将该位置与中心点之间的距离一并返回
  - `ASC|DESC`：可选参数，添加 `ASC` 将返回的匹配位置根据距离从近到远排序，`DESC` 则相反
  - `COUNT`：可选参数，限制结果数量
- 指定集合中某个位置范围查询位置信息：
  - 命令：`GEORADIUSBYMEMBER location-set location radius m|km|ft|mi [WITHCOORD] [WITHDIST] [ASC|DESC] [COUNT count]`
  - 参数和 `GEORADIUS ` 用法一致

****

### 应用场景

****

存储不同位置信息：

- 添加武汉的坐标信息到 `hubeiCities` 集合中：`GEOADD hubeiCities 114.32538 30.534535 wuhan`
- 连续添加多个：`GEOADD hubeiCities 112.161882 32.064505 xiangyang 111.305197 30.708127 yichang 111.583717 30.463363 zhijiang`

获取位置信息：

- 查询武汉市的位置信息：`GEOPOS hubeiCities wuhan` 结果返回经度和纬度信息
- 连续查询多个：`GEOPOS hubeiCities xiangyang yichang zhijiang` 

指定范围查询位置信息：

- 查找 `hubeiCities` 集合中 112.927076 28.235653 (长沙) 500km 以内的位置信息，查找结果中应包含不超过 5 个位置的坐标信息，距离信息，并按距离由近到远排序：`GEORADIUS hubeiCities 112.927076 28.235653 500 km withcoord withdist asc count 5`
- 在 `hubeiCities` 位置集合中查找距离武汉200km 以内的位置信息（这里指定的目标位置只能是 `hubeiCities` 中存在的位置，而不能指定位置坐标），查找结果中应包含不超过 2 个位置的坐标信息，距离信息，并按距离由远到近排序：`GEORADIUSBYMEMBER hubeiCities wuhan 200 km withcoord withdist desc count 2`

****

# Redis 高级应用

****

## 发布订阅

****

### 基础概念

****

Redis 提供了发布订阅功能，可以用于消息的传输。

Redis的发布订阅机制包括三个部分：

![image-20240316163342853](https://image.itbaima.cn/images/40/image-20240316162308618.png)

publisher：

- 发布者，是发送信息或数据的一方
- 在Redis中，发布者可以是任何客户端
- 发布者通过 `PUBLISH` 命令将消息发送到一个特定的频道

subscriber：

- 订阅者，是接收信息或数据的一方
- 订阅者可以 "订阅" 一个或多个频道，以便接收发布者发送的消息
- 订阅者使用 `SUBSCRIBE` 命令订阅自己感兴趣的频道

channel：

- 通道，是一种传输信息或数据的媒介
- 通道是发布者和订阅者之间的桥梁，发布者通过通道将信息发送到订阅者
- 通道没有明确的创建和销毁步骤：当有客户端订阅一个频道时，该频道就存在；当最后一个订阅该频道的客户端取消订阅，该频道并不立即消失，但是没有任何作用

****

### 指令详情

****

- 订阅消息：`SUBSCRIBE channel1 channel2`，Redis 客户端 `channel1` 订阅 客户端 `channel2`
- 发布消息：`PUBLISH channel message ` ，Redis 客户端 `channel` 发布一条 `message`，订阅了该 `channel` 的客户端将收到 `message`
- 退订：`UNSUBSCRIBE channel`，退订 `channel`，不再接收来自 `channel` 的消息
- 模式匹配订阅：`PSUBSCRIBE ch*`，根据正则表达式匹配订阅，订阅所有以 `ch` 开头的 `channel`
- 模式匹配退订：`PUNSUBSCRIBE ch*`，根据正则表达式匹配退订，退订所有以 `ch` 开头的 `channel`

****

### 使用场景

****

在 Redis 哨兵模式中，哨兵通过发布与订阅的方式与 Redis 主服务器和 Redis 从服务器进行通信

Redisson是一个分布式锁框架，在 Redisson 分布式锁释放的时候，是使用发布与订阅的方式通知的

**注意**：如果是注重业务的消息，推荐用消息队列实现

****

## Redis 事务

****

### 基础概念

****

Redis事务的本质是一组命令的集合：

- Redis 的事务是通过 multi、exec、discard 和 watch这四个命令来完成的
- Redis 的单个命令都是原子性的，所以这里需要确保事务性的对象是命令集合
- Redis 将命令集合序列化并确保处于同一事务的命令集合连续且不被打断的执行
- Redis 不能保障失败回滚

**注意**：Redis 的事务远远弱于 mysql，严格意义上，它不能叫做事务，只是一个命令打包的批处理，不能保障失败回滚

****

### 原理分析

****

**事务的创建机制**：

- 调用 `multi` 命令，实际上会开启一个命令队列，后续的命令将被视为事务操作添加到该命令队列
- 如果期间出现问题，则会终止操作并清空队列
- 执行 `exec` 命令，则批量提交队列中的命令，事务完成
- 若执行 `discard`，则不执行命令，直接清空队列

**事务的回滚机制**：

- 如果命令队列中的命令出现语法错误，Redis 2.6.5 之前的版本不会回滚，之后的版本会将整个事务回滚
- 如果是事务执行期间的错误，Redis 不会回滚，其他正确的指令会继续执行

**watch监听机制**;

- 该命令用于监视一个（或多个）key，如果在事务执行之前这个（或这些）key 被其他命令所改动，那么事务将被打断
- `watch` 命令可以通过监控某个 key 的变动，来决定是不是回滚
- 主要应用于高并发的正常业务场景下，处理并发协调

****

## LUA  脚本

****

### 基础概念

****

LUA  是一种轻量小巧的脚本语言，用标准 c 语言编写并以源代码形式开放，其设计目的是为了嵌入应用程序中，从而为应用程序提供灵活
的扩展和定制功能。

由于 Redis 回滚机制并不完善，因此用 Redis 的事务一般引入 LUA  脚本来实现：

- Redis 会将整个 LUA  脚本作为一个整体执行，中间不会被其他命令插入
- 因此在编写脚本的过程中无需担心会出现竞态条件，无需使用事务，能够保证原子性

****

### EVAL 命令

****

自 2.6.0 起可用，通过内置的 LUA  编译/解释器，可以使用 EVAL 命令对 LUA  脚本进行求值：

- 命令格式：`EVAL script numkeys key [key ...] arg [arg ...]`
- `script`：该参数是一段 LUA  5.1 脚本程序，脚本不必（也不应该）定义为一个 LUA  函数
- `numkeys` ：用于指定键名参数的个数
- `key`：需要操作的键，可以指定多个，在 LUA  脚本中通过 `KEYS[1]`、`KEYS[2]` 获取
- `arg`：附件的参数，可以指定多个，在 LUA  脚本中通过 `ARGS[1]`、`ARGS[2]` 获取

****

###  LUA  脚本中调用 Redis 命令

****

- `redis.call()`：
  - 返回值就是 redis 命令执行的返回值
  - 例如，`redis.call('SET', 'KEY:A', '114514')`
  - 如果出错，则返回错误信息，不继续执行
- `redis.pcall()`:
  - 返回值就是redis命令执行的返回值
  - 例如，`redis.pcall('GET', 'KEY:A')`
  - 如果出错，则记录错误信息，继续执行

**注意**：脚本中，使用 return 语句将返回值返回给客户端，如果没有 return，则返回 nil

****

## 慢查询日志

****

### 客户端请求的生命周期

****

![image-20240316175527785](https://image.itbaima.cn/images/40/image-20240316178250131.png)

**注意**：

- 慢查询只统计 步骤3 执行命令的时间，所以没有慢查询并不代表客户端没有超时问题
- 换句话说 Redis 的慢查询记录时间指的是不包括客户端响应、发送回复等 IO 操作，而单单是执行一个查询命令所耗费的时间

****

### 慢查询设置

****

**慢查询配置相关的参数**

- `slowlog-log-slower-than`：
  - 选项指定执行时间超过多少微秒的命令请求会被记录到日志上
  - 例如，`slowlog-log-slower-than 100`，执行时间超过100微秒的命令就会被记录到慢查询日志
- `slowlog-log-max-len`：
  - 选项指定服务器最多保存多少条慢查询日志
  - 服务器使用**先进先出**的方式保存多条慢查询日志、
  - 当服务器储存的慢查询日志数量等于 `slowlog-log-max-len` 值时，服务器在添加一条新的慢查询日志之前，会先将最旧的一条慢查询日志删除

上述配置，在 Redis 中有两种修改方法：

- 一种是直接修改配置文件
- 另一种是使用 `config set` 命令动态修改：`config set slowlog-log-slower-than 100`

**查看慢查询日志**：

- `slowlog get`：查看慢查询日志，`slowlog get 10` 查看最新的 10 条慢查询记录

****

### 慢查询日志的组成

****

![image-20240316180948773](https://image.itbaima.cn/images/40/image-20240316184595898.png)

```shell
1) 1) 3                // 表示这是第三个被记录的慢查询
2) 1710583725          // Unix 时间戳，表示该慢查询发生的具体时间
3) 5				   // 代表查询执行的时长，单位为 ms
4) 1) "set"			   // 具体的 Redis 命令
2) "b"				   // 命令的 参数
3) "a"
5) "127.0.0.1:2474"    // 发出此指令的客户端的 IP 地址和端口号
6) ""          		   // 代表该查询所在的数据库 ID，"" 表示默认数据库
```

****

# 持久化原理

****

## 持久化流程

****

Redis 是基于内存的数据库，数据存储在内存中，为了避免进程退出导致数据永久丢失，需要定期对内存中的数据以某种形式从内存呢保存到磁盘当中；当 Redis 重启时，利用持久化文件实现数据恢复。

Redis 的持久化主要有以下流程：

- 客户端向服务端发送写操作数据
- 数据库服务端接收到写请求的数据
- 服务端调用 write 这个系统调用，将数据往磁盘上写
- 操作系统将缓冲区中的数据转移到磁盘控制器上
- 磁盘控制器将数据写到磁盘的物理介质

上述流程中，数据的传播过程为：`客户端内存 -> 服务端内存 -> 系统内存缓冲区 -> 磁盘缓冲区 -> 磁盘`

在理想条件下，上述过程是一个正常的保存流程，但是在大多数情况下，我们的机器等等都会有各种各样的故障，这里划分两种情况：

- Redis 数据库发生故障，只要在上面的第三步执行完毕，那么就可以持久化保存，剩下的两步由操作系统替我们完成
- 操作系统发生故障，必须上面 5 步都完成才可以

为了应对以上 5 步操作，Redis 提供了两种不同的持久化方式：RDB(Redis DataBase) 和 AOF(Append Only File)。

****

## RDB 原理

****

### 基础概念

****

RDB 是 Redis 默认开启的全量数据快照保存方案：

- 每隔一段时间，将当前进程中的数据生成快照保存到磁盘（快照持久化），生成一个文件后缀名为 rdb 的文件
- 当 Redis 重启时，可以读取快照文件进行恢复

关于 RDB 的配置均保存在 redis.conf 文件中，可以进行修改

****

### 触发机制及原理

****

![image-20240316233803329](https://image.itbaima.cn/images/40/image-20240316237749003.png)



通过 `SAVE` 命令手动触发 RDB，这种方式会阻塞 Redis 服务器，直到 RDB 文件创建完成，线上禁止使用这种方式

![image-20240316234108131](https://image.itbaima.cn/images/40/image-20240316231784272.png)

通过 `BGSAVE` 命令，这种方式会 fork 一个子进程，由子进程负责持久化过程，因此阻塞只会发生在 fork 子进程的时候

**注意**：

- 子进程不直接拷贝硬盘数据，而是拷贝父进程的页表，但实际上仍然和父进程共享同一物理地址（共享数据）
- 子进程执行 bgsave 操作会生成临时的 RDB 文件，不会直接修改原有的 RDB 文件
- 为了避免脏写，这里 fork 时又引入了 copy-on-write 的技术：
  - 主进程读操作访问共享内存，此时不会复制数据
  - 主进程发生写操作，会复制一份物理地址的数据副本进行写入，子进程仍然读取原来的旧版数据

除了上述指令手动执行外，Redis 还可以根据 redis.conf 文件的配置自动触发：

- 设置 redis.conf 中的 `save x y`：表示 x 秒内，至少有 y 个 key 值变化，则触发 bgsave
- 当发生主从节点复制时，从节点申请同步，主节点会触发 bgsave 操作，将生成的文件快照发送给从节点
- 执行 Debug reload 命令重新加载 redis  时，也会触发 bgsave 操作
- 默认情况下，执行了 shutdown 指令，如果没有开启 AOF 持久化，则也会触发 bgsave 操作

****

## AOF 原理

****

### 基础概念

****

AOF 是 Redis 默认未开启的持久化策略： 

- 以日志的形式来记录用户请求的写操作，读操作不会记录，因为写操作才会存储
- 文件以追加的形式而不是修改的形式
- redis 的  AOF 恢复其实就是把追加的文件从开始到结尾读取执行写操作

****

### 持久化原理

****

![image-20240317002048890](https://image.itbaima.cn/images/40/image-20240317001981695.png)





AOF 的持久化实现原理分为四大步骤：

- 命令追加：所有的命令都会被追加到 AOF 缓冲当中
- 文件同步：AOF 缓冲区根据对应的策略向磁盘进行同步操作
- 文件重写：随着同步的进行，AOF 文件追加的命令会越来越多，导致文件臃肿，会触发重写以便减小文件体积
- 重启恢复：当 Redis 重启时，会重新加载 AOF 执行命令恢复数据

**注意**：

- AOF 默认是关闭的，修改 redis.conf 文件的 `appendonly yes` 即可开启
- 频率配置：
  - `always` 同步刷盘：数据可靠，但性能影响大
  - `everysec` 每秒刷盘：性能适中，最多丢失一秒数据
  - `no` 系统控制刷盘：性能最好，可靠性差，容易丢失大量数据
- 设置重写：
  - 用 `bgrewriteaof` 重写 AOF 文件，用最少命令达到相同效果
  - 可设置文件大小到大一定阈值自动触发

****

### AOF 数据恢复过程

****

已知 Redis 通过重新执行一遍 AOF 文件里面的命令进行还原状态，但实际上 Redis 并不是直接执行的：

![image-20240317100853235](https://image.itbaima.cn/images/40/image-20240317104847361.png)



具体步骤如下：

- 首先创建一个不带有网络链接的伪客户端，此过程只需要载入 AOF 文件即可，因此无需网络连接
- 之后读取一条 AOF 文件中的命令并使用伪客户端执行
- 重复上述过程，直到 AOF 文件所有的命令执行完毕

****

### AOF 文件重写过程

****

为了解决 AOF 文件持续追加命令导致 AOF 文件过度膨胀的问题，Redis 提供了 AOF 文件重写功能

![image-20240317101252346](https://image.itbaima.cn/images/40/image-20240317102079300.png)

例如上述命令在执行重写前，会记录 `list` 这个 `key` 的状态，重写前 AOF 要保存这五条命令，重写后只需要一条命令，结果确是等价的。

**注意**：

- AOF 重写的过程并不是针对现有的 AOF 文件读取、分析或写入操作，而是读取服务器当前数据库的状态来实现
- 例如，首先从数据库中读取当前键的值，然后用一条命令记录键值对，以此代替记录这个键值对的多条命令

**触发机制**：

- 手动：使用命令 `bgrewriteaof` ，如果当前有正在运行的 rewrite 子进程，则本次的重写会延迟执行，否者直接触发
- 自动触发：根据配置规则 `auto-aof-rewrite-min-size 64mb`，若 AOF 文件超过配置大小则会自动触发

****

### AOF 重写原理

****

AOF 重写函数会进行大量的写入操作，调用该函数的线程将被长时间阻塞，所以 Redis 在子进程中执行 AOF 重写操作：

![image-20240317102201903](https://image.itbaima.cn/images/40/image-20240317106231020.png)

在整个 AOF 重写的过程中，只有信号处理函数的执行过程会对 Redis 主进程造成阻塞，在其他时候都不会阻塞主进程

![image-20240317102837810](https://image.itbaima.cn/images/40/image-20240317101795130.png)

****

## 持久化优先级

****

首先对比一下两种持久化方式的优缺点：

- 文件大小：RDB 文件默认使用 LZF 算法进行压缩，压缩后的文件体积远远小于内存大小，适用于备份、全量复制等
- 恢复速度：Redis 加载 RDB 文件恢复数据要远远快于AOF 方式，AOF 则需要执行全部的命令
- 内存占用：两种方式都需要 fork 出子进程，子进程属于重量级操作，频繁执行的成本较高
- 备份容灾：RDB 文件为二进制文件，没有可读性，AOF 文件在了解其结构的情况下可以手动修改或者补全
- 数据一致性：RDB 方式的实时性不够，无法做到秒级的持久化，存在丢失数据的风险，AOF 可以做到最多丢失一秒的数据

在服务器同时开启了 RDB 和 AOF 的情况下，会优先选择 AOF 方式，若不存在 AOF 文件，则会执行 RDB 恢复。

****

## RDB 混合 AOF 解决方案

****

针对上述 RDB 和 AOF 的持久化原理可知，两者都需要 fork 出子进程，可能会造成主进程的阻塞，因此需要：

- 降低 fork 的频率，手动触发 RDB 快照或 AOF 重写
- 控制 Redis 内存限制，防止 fork 耗时过长
- 配置 Linux 的内存分配策略，避免因为物理内存不足导致 fork 失败

除此之外，在线上环境中，如果不是特别敏感的数据或可以通过重新生成的方式恢复数据，则可以关闭持久化

对于其他场景，Redis 在 4.0 引入了 RDB 混合 AOF 的解决方案——混合使用 AOF 日志和内存快照：

- 在 redis.conf 里面开启配置：`aof-use-rdb-preamble yes`

当开启混合持久化时，在 AOF 重写日志时，fork 出来的子进程会先将与主线程共享的内存数据以 RDB 的方式写入 AOF，然后主线程处理的操作命令会被记录在重写缓冲区里，重写缓冲区的增量命令会以 AOF 的方式写入 AOF 文件，写入完成后，通知主进程将新的含有RDB 格式和 AOF 格式的 AOF 文件替换旧的 AOF 文件。

**注意**：对于采用混合持久化方案的 AOF 文件，AOF 文件的前半部分是 RDB 格式的全量数据，后半部分则是 AOF 格式的增量数据。

这样的好处在于，由于前半段为 RDB 格式的文件，恢复速度较快，加载完 RDB 的内容后再执行后半部分 AOF 的内容，以减少的丢失数据的风险。

****

# 安全策略

****

## 密码认证

****

可以通过 Redis 的配置文件设置密码参数，当客户端连接到 Redis 服务器时，需要密码验证：

- 打开 redis.conf，找到 `requirepass`  进行配置
- 密码要求：长度 8 位以上，包含四类中的三类字符（字母大小写，数字，符号）

配置完毕后，重启生效。

也可以通过命令的方式修改：

- `CONFIG SET requirepass password`
- 登陆时需要：`AUTH password`

**注意**：

- 这里修改的密码为 default 用户密码

- 在 initServer 中会调用 ACLUpdateDefaultUserPassword(server.requirepass) 函数设置 default 用户的密码

- ```
  /* Set the password for the "default" ACL user. This implements supports for
   * requirepass config, so passing in NULL will set the user to be nopass. */
  void ACLUpdateDefaultUserPassword(sds password) {
      ACLSetUser(DefaultUser,"resetpass",-1);
      if (password) {
          sds aclop = sdscatlen(sdsnew(">"), password, sdslen(password));
          ACLSetUser(DefaultUser,aclop,sdslen(aclop));
          sdsfree(aclop);
      } else {
          ACLSetUser(DefaultUser,"nopass",-1);
      }
  }
  ```

****

## 密码不生效解决方案

****

查看 redis.conf 配置：

```shell
# IMPORTANT NOTE: starting with Redis 6 "requirepass" is just a compatibility
# layer on top of the new ACL system. The option effect will be just setting
# the password for the default user. Clients will still authenticate using
# AUTH <password> as usually, or more explicitly with AUTH default <password>
# if they follow the new protocol: both will work.
#
# The requirepass is not compatible with aclfile option and the ACL LOAD
# command, these will cause requirepass to be ignored.
#
# requirepass foobared
```

自 Redis 6.0 起，`requirepass` 只是针对 default 用户的配置，由于 redis 加载配置后会读取 aclfile，重新新建全局 Users 对象，此举会调用 ACLInitDefaultUser 函数重新新建 nopass 的 default 用户，因此导致配置的 `requirepass` 失效

根据上述分析，解决方案很明显：

- 更改启动 redis 的方式，不读取 aclfile：`redis-server ./redis.conf`
- 或者在启用 aclfile 的情况下，redis-cli 登录后，用 `config set requirepass xxx`，然后 `acl save`（会写 default 的 user 规则到 aclfile 中）

****

# 过期策略

****

## 基础操作

****

Redis 的 key 存在过期时间，设置命令如下：

- `expire <key> <n>`：设置 key 在 n 秒后过期
- `pexpire <key> <n>`：设置 key 在 n 毫秒后过期
- `expireat <key> <n>`：设置 key 在某个时间戳（精确到秒）后过期
- `pexpireat <key> <n>`：设置 key 在某个时间戳（精确到毫秒）后过期

也可以在 key 创建时直接设置：

- `set <key> <value> ex <n>`：设置键值对的时候，同时指定过期时间（精确到秒）
- `set <key> <value> px <n>`：设置键值对的时候，同时指定过期时间（精确到毫秒）
- `setex <key> <n> <va1ue>`：设置键值对的时候，同时指定过期时间（精确到秒），该操作是一个原子操作

其他相关操作：

- `persist <key>`：将 key 的过期时间删除
- `TTL <key>`：返回 key 的剩余生存时间（精确到秒）
- `PTTL <key>`：返回 key 的剩余生存时间（精确到毫秒）

****

## Redis 过期删除策略

****

要想删除一个过期的 key，首先需要判断它是否过期：

- 在 Redis 内部，当我们给某个 key 设置过期时间时，Redis 会给该 key 带上过期时间存入一个过期字典（redisdb）中
- 每次查询一个 key 时，Redis 会先从过期字典查询该键是否存在：
  - 不存在则正常返回
  - 存在则取该 key 的时间和当前系统时间对比判定是否过期
- 对于过期的 key 会根据过期删除策略进行处理

Redis 提供了三种过期策略：

- 惰性删除：只有当客户端尝试获取一个 key 时，Redis才会检查该 key 是否过期，如果过期则删除
- 定时删除：在设定key的过期时间的同时，创建一个定时器，当达到过期时间时，定时器立即删除该 key
- 定期删除：每隔一段时间随机取出一定数量的 key 进行检查，并删除过期的 key

而 Redis 的过期删除策略是：惰性删除 + 定期删除

****

### 惰性删除原理

****

查看 Redis 源码 db.c，其中执行惰性删除的逻辑会反复调用 `expireIfNeeded` 函数对 key 其进行检查：

```c
/* Return values for expireIfNeeded */
typedef enum {
    KEY_VALID = 0, /* Could be volatile and not yet expired, non-volatile, or even non-existing key. */
    KEY_EXPIRED, /* Logically expired but not yet deleted. */
    KEY_DELETED /* The key was deleted now. */
} keyStatus;

keyStatus expireIfNeeded(redisDb *db, robj *key, int flags) {
    if (server.lazy_expire_disabled) return KEY_VALID;  // 未设置过期策略直接返回 key 值
    if (!keyIsExpired(db,key)) return KEY_VALID;

    /* If we are running in the context of a replica, instead of
     * evicting the expired key from the database, we return ASAP:
     * the replica key expiration is controlled by the master that will
     * send us synthesized DEL operations for expired keys. The
     * exception is when write operations are performed on writable
     * replicas.
     *
     * Still we try to return the right information to the caller,
     * that is, KEY_VALID if we think the key should still be valid, 
     * KEY_EXPIRED if we think the key is expired but don't want to delete it at this time.
     *
     * When replicating commands from the master, keys are never considered
     * expired. */
    // 这里说明了，从节点的 key 过期策略是由主节点控制的，如果是在复制主节点的命令时，键永远不会被视为已过期
    if (server.masterhost != NULL) {   
        if (server.current_client && (server.current_client->flags & CLIENT_MASTER)) return KEY_VALID;
        if (!(flags & EXPIRE_FORCE_DELETE_EXPIRED)) return KEY_EXPIRED;
    }

    /* In some cases we're explicitly instructed to return an indication of a
     * missing key without actually deleting it, even on masters. */
    if (flags & EXPIRE_AVOID_DELETE_EXPIRED)
        return KEY_EXPIRED;

    /* If 'expire' action is paused, for whatever reason, then don't expire any key.
     * Typically, at the end of the pause we will properly expire the key OR we
     * will have failed over and the new primary will send us the expire. */
    if (isPausedActionsWithUpdate(PAUSE_ACTION_EXPIRE)) return KEY_EXPIRED;

    /* The key needs to be converted from static to heap before deleted */
    int static_key = key->refcount == OBJ_STATIC_REFCOUNT;
    if (static_key) {
        key = createStringObject(key->ptr, sdslen(key->ptr));
    }
    /* Delete the key */
    deleteExpiredKeyAndPropagate(db,key);
    if (static_key) {
        decrRefCount(key);
    }
    return KEY_DELETED;
}
```

****

### 定期删除原理

****

查看 Redis 源码 expire.c，其中执行定期删除的逻辑在 `void activeExpireCycle(int type)` 中：

```c
void activeExpireCycle(int type) {
    /* Adjust the running parameters according to the configured expire
     * effort. The default effort is 1, and the maximum configurable effort
     * is 10. */
    unsigned long
    effort = server.active_expire_effort-1, /* Rescale from 0 to 9. */
    
    // 每次循环取出过期键的数量
    config_keys_per_loop = ACTIVE_EXPIRE_CYCLE_KEYS_PER_LOOP +
                           ACTIVE_EXPIRE_CYCLE_KEYS_PER_LOOP/4*effort,
    // FAST 模式下的执行周期
    config_cycle_fast_duration = ACTIVE_EXPIRE_CYCLE_FAST_DURATION +
                                 ACTIVE_EXPIRE_CYCLE_FAST_DURATION/4*effort,
    
    // SLOW 模式的执行周期
    config_cycle_slow_time_perc = ACTIVE_EXPIRE_CYCLE_SLOW_TIME_PERC +
                                  2*effort,
    config_cycle_acceptable_stale = ACTIVE_EXPIRE_CYCLE_ACCEPTABLE_STALE-
                                    effort;
    ...........
```

定期删除的周期配置在 redis.conf 中，其中 `hz 10` 默认值每秒进行 10 次过期检查

****

## Redis 内存淘汰策略

****

当 Redis 运行内存超过设置的最大内存时，会执行淘汰策略删除符合条件的 key 保障高效运行

最大内存设置：redis.conf 中 `maxmemory <bytes>`，若不设置默认无限制（但最大为物理内存的四分之三）

Redis 支持八种淘汰策略：

- noeviction：不删除任何数据，内存不足直接报错 (默认策略)
- volatile-lru：挑选最近最久使用的数据淘汰
- volatile-lfu：挑选最近最少使用数据淘汰 
- volatile-ttl：挑选将要过期的数据淘汰
- volatile-random：任意选择数据淘汰
- allkeys-lru：挑选最近最少使用的数据淘汰
- allkeys-lfu：挑选最近使用次数最少的数据淘汰
- allkeys-random：任意选择数据淘汰，相当于随机

****

### LRU 算法原理

****

LRU 全称为 Least Recently Used，最近最少使用，会选择淘汰最近最少使用的数据

传统LRU算法实现：

- 基于链表的结构，链表中的元素按照操作顺序从前向后排列，最新操作的键会被移动到表头
- 当需要执行淘汰策略时，删除链表尾部的元素即可

但是 Redis 的 LRU 算法并不是传统的算法实现，在海量数据下，基于链表的操作会带来额外的内存开销，降低缓存性能

因此，Redis 采用了一种近似 LRU 算法

****

首先来看一下 Redis 源码中 server.h 中对 redisObject 的定义：

```c
struct redisObject {
    unsigned type:4;
    unsigned encoding:4;
    unsigned lru:LRU_BITS; /* LRU time (relative to global lru_clock) or
                            * LFU data (least significant 8 bits frequency
                            * and most significant 16 bits access time). */
    int refcount;
    void *ptr;
};
```

其中 lru 的值在创建对象时会被初始化，在 object.c 中：

```c
// typedef struct redisObject robj;
robj *createObject(int type, void *ptr) {
    robj *o = zmalloc(sizeof(*o));
    o->type = type;
    o->encoding = OBJ_ENCODING_RAW;
    o->ptr = ptr;
    o->refcount = 1;
    o->lru = 0;
    return o;
}

void initObjectLRUOrLFU(robj *o) {
    if (o->refcount == OBJ_SHARED_REFCOUNT)
        return;
    /* Set the LRU to the current lruclock (minutes resolution), or
     * alternatively the LFU counter. */
    if (server.maxmemory_policy & MAXMEMORY_FLAG_LFU) {
        o->lru = (LFUGetTimeInMinutes() << 8) | LFU_INIT_VAL;
    } else {
        o->lru = LRU_CLOCK();
    }
    return;
}
```

Redis 在每一个对象的结构体中添加了  lru 字段，用于记录此数据最后一次访问的时间戳，这里是基于全局 LRU 时钟计算的

如果一个 key 被访问了，则会调用 db.c 中的 `lookupKey` 函数对 lru 字段进行更新：

```c
robj *lookupKey(redisDb *db, robj *key, int flags) {
    // 通过 dbFind 函数查找给定的键（key）如果找到，则获取键对应的值
    dictEntry *de = dbFind(db, key->ptr);
    robj *val = NULL;
    if (de) {
        val = dictGetVal(de);
        /* Forcing deletion of expired keys on a replica makes the replica
         * inconsistent with the master. We forbid it on readonly replicas, but
         * we have to allow it on writable replicas to make write commands
         * behave consistently.
         *
         * It's possible that the WRITE flag is set even during a readonly
         * command, since the command may trigger events that cause modules to
         * perform additional writes. */
        
        // 处理键过期的情况
        int is_ro_replica = server.masterhost && server.repl_slave_ro;
        int expire_flags = 0;
        if (flags & LOOKUP_WRITE && !is_ro_replica)
            expire_flags |= EXPIRE_FORCE_DELETE_EXPIRED;
        if (flags & LOOKUP_NOEXPIRE)
            expire_flags |= EXPIRE_AVOID_DELETE_EXPIRED;
        if (expireIfNeeded(db, key, expire_flags) != KEY_VALID) {
            /* The key is no longer valid. */
            val = NULL;
        }
    }

    if (val) {
        /* Update the access time for the ageing algorithm.
         * Don't do it if we have a saving child, as this will trigger
         * a copy on write madness. */
        // 更新访问时间
        if (server.current_client && server.current_client->flags & CLIENT_NO_TOUCH &&
            server.current_client->cmd->proc != touchCommand)
            flags |= LOOKUP_NOTOUCH;
        if (!hasActiveChildProcess() && !(flags & LOOKUP_NOTOUCH)){
            if (server.maxmemory_policy & MAXMEMORY_FLAG_LFU) {
                updateLFU(val);         // 策略为 LFU，更新使用频率
            } else {
                val->lru = LRU_CLOCK();  // 策略为 LRU，更新时间戳 
            }
        }

        if (!(flags & (LOOKUP_NOSTATS | LOOKUP_WRITE)))
            server.stat_keyspace_hits++;
        /* TODO: Use separate hits stats for WRITE */
    } else {
        if (!(flags & (LOOKUP_NONOTIFY | LOOKUP_WRITE)))
            notifyKeyspaceEvent(NOTIFY_KEY_MISS, "keymiss", key, db->id);
        if (!(flags & (LOOKUP_NOSTATS | LOOKUP_WRITE)))
            server.stat_keyspace_misses++;
        /* TODO: Use separate misses stats and notify event for WRITE */
    }

    return val;
}
```

当 Redis 进行内存淘汰时，会使用随机采样的方式来淘汰数据，查看源码 evict.c：

```c
struct evictionPoolEntry {
    unsigned long long idle;    /* Object idle time (inverse frequency for LFU) */
    sds key;                    /* Key name. */
    sds cached;                 /* Cached SDS object for key name. */
    int dbid;                   /* Key DB number. */
    int slot;                   /* Slot. */
};
```

这里定义了一个淘汰池，所有待淘汰的 key 会通过 `evictionPoolPopulate` 函数填入：

```c
int evictionPoolPopulate(redisDb *db, kvstore *samplekvs, struct evictionPoolEntry *pool) {
    int j, k, count;
    dictEntry *samples[server.maxmemory_samples];

    int slot = kvstoreGetFairRandomDictIndex(samplekvs);
    
    // 从字典中获取一些键，结果存放到 samples 中，并且返回获取的键的数量。所选取的键的数量不能超过 server.maxmemory_samples
    count = kvstoreDictGetSomeKeys(samplekvs,slot,samples,server.maxmemory_samples);
    // 循环采样，对抽样得到的键进行处理
    for (j = 0; j < count; j++) {
        unsigned long long idle;
        sds key;
        robj *o;
        dictEntry *de;

        de = samples[j];
        key = dictGetKey(de);

        /* If the dictionary we are sampling from is not the main
         * dictionary (but the expires one) we need to lookup the key
         * again in the key dictionary to obtain the value object. */
        if (server.maxmemory_policy != MAXMEMORY_VOLATILE_TTL) {
            if (samplekvs != db->keys)
                de = kvstoreDictFind(db->keys, slot, key);
            o = dictGetVal(de);
        }
        ............
```

****

### LFU 算法原理

****

LFU 全称 Least Frequently Used，最近最不常用，LFU 算法是根据数据访问次数来淘汰数据的，它的核心思想是“如果数据过去
被访问多次，那么将来被访问的频率也更高”

传统 LFU 算法实现：

- 基于链表的结构，链表中的元素按照访问的次数从大到小排序，新插入的元素在尾部，访问后次数加一
- 当需要执行淘汰策略时，对链表进行排序，相同次数按照时间排序，删除访问次数最少的尾部元素

Redis 实现的 LFU 算法也是一种近似 LFU 算法

****

首先，仍然从 Redis 源码中 server.h 中对 redisObject 的定义入手：

```c
struct redisObject {
    unsigned type:4;
    unsigned encoding:4;
    unsigned lru:LRU_BITS; /* LRU time (relative to global lru_clock) or
                            * LFU data (least significant 8 bits frequency
                            * and most significant 16 bits access time). */
    int refcount;
    void *ptr;
};
```

之前在 LRU 算法原理时我仅仅提到 lru 字段作为 LRU 算法的时间戳来使用，但如果选择 LFU 算法，该字段将被拆分为两部分：

- 低 8 位：计数器，被设置为宏定义 LFU_INIT_VAL = 5
- 高 16 位：以分钟为精度的 Unix 时间戳

之后仍然是 db.c 中的 `lookupKey` 函数，这次具体来看 LRU 的更新策略：

```c
		if (!hasActiveChildProcess() && !(flags & LOOKUP_NOTOUCH)){
            if (server.maxmemory_policy & MAXMEMORY_FLAG_LFU) {
                updateLFU(val);         // 策略为 LFU，更新使用频率
            } else {
                val->lru = LRU_CLOCK();  // 策略为 LRU，更新时间戳 
            }
        }
```

更新策略为调用了 `updateLFU`：

```c
void updateLFU(robj *val) {
    // 根据距离上次访问的时长，衰减访问次数
    unsigned long counter = LFUDecrAndReturn(val);
    // 根据当前访问更新访问次数
    counter = LFULogIncr(counter);
    // 更新 lru 变量值
    val->lru = (LFUGetTimeInMinutes()<<8) | counter;
}
```

Redis 执行 LFU 淘汰策略和 LRU 基本类似，也是将所有待淘汰的 key 通过 `evictionPoolPopulate` 函数填入，区别在于填充策略的选择：

```c
        /* Calculate the idle time according to the policy. This is called
         * idle just because the code initially handled LRU, but is in fact
         * just a score where a higher score means better candidate. */
        if (server.maxmemory_policy & MAXMEMORY_FLAG_LRU) {
            idle = estimateObjectIdleTime(o);
        } else if (server.maxmemory_policy & MAXMEMORY_FLAG_LFU) {
            /* When we use an LRU policy, we sort the keys by idle time
             * so that we expire keys starting from greater idle time.
             * However when the policy is an LFU one, we have a frequency
             * estimation, and we want to evict keys with lower frequency
             * first. So inside the pool we put objects using the inverted
             * frequency subtracting the actual frequency to the maximum
             * frequency of 255. */
            idle = 255-LFUDecrAndReturn(o);
        } else if (server.maxmemory_policy == MAXMEMORY_VOLATILE_TTL) {
            /* In this case the sooner the expire the better. */
            idle = ULLONG_MAX - (long)dictGetVal(de);
        } else {
            serverPanic("Unknown eviction policy in evictionPoolPopulate()");
        }
```

****

# Redis 高可用

****

## 主从复制解决方案

****

将一台 Redis 服务器的数据，复制到其他的 Redis 服务器，前者称为主节点（master），其他服务器称为从节点（slave）。

**注意**：主从复制的数据流动是单向的，只能从主节点流向从节点

Redis 的主从复制是异步复制，异步分为两个方面：

- 一个是 master 服务器在将数据同步到 slave 时是异步的，因此 master 服务器在这里仍然可以接收其他请求，
- 一个是 slave 在接收同步数据也是异步的

![image-20240317203824839](https://image.itbaima.cn/images/40/image-20240317206779610.png)

一主多从：

- 一个主节点：负责数据修改操作
- 多个从节点：负责读数据，一般多为一主一从的配置

如果从节点需求大，由于主从同步时，主节点需要发送自己的 RDB 文件给从节点进行同步，若此时从节点数量过多，主节点需要频繁地进行 RDB 操作，会影响主节点的性能。

因此，考虑从节点再做为主节点配置从节点：

![image-20240317204034161](https://image.itbaima.cn/images/40/image-20240317209598665.png)

****

### 全量同步原理

****

全量同步发生在主节点和从节点的第一次同步

![image-20240317205108370](https://image.itbaima.cn/images/40/image-20240317206270608.png)

- 从节点向主节点发起同步请求
- 主节点先返回 replid 给从节点更新
- 然后主节点执行 bgsave 生成 RDB 文件发送给从节点
- 从节点删除本地数据，接收 RDB 文件并加载
- 同步过程中若主节点收到新的命令也会写入从节点的缓冲区中
- 从节点将缓冲区的命令写入本地，记录最新数据到 offset

****

### 增量同步原理

****

因为各种原因 master 服务器与 slave 服务器断开后，slave 服务器在重新连上 master 服务器时会尝试重新获取断开后未同步的数据
即部分同步，或者称为部分复制。

![image-20240317205647198](https://image.itbaima.cn/images/40/image-20240317203401648.png)

- master 服务器会记录一个 replicationId 的伪随机字符串，用于标识当前的数据集版本，还会记录一个当数据集的偏移量 offset
- 主节点不断滴把自己接收到的命令记录在 repl_backlog 中，并修改 offset
- 执行增量同步时，主节点在 repl_backlog 获取 offset 后的数据并返回给从节点
- 从节点接收数据后写入本地，修改 offset 与主节点一致

**注意**：

- epl_backlog 大小有上限，超过后新数据会覆盖老数据
- 如果从节点断开时间太久导致未备份的数据被覆盖则无法基于 log 做增量同步

****

## Sentinel 哨兵解决方案

****

对于主从同步解决方案，如果主节点因为某种原因宕掉，从节点也无法承担主节点的任务，导致整个系统无法正常执行业务

因此引入 Sentinel，若主节点宕掉，则 Sentinel 会从节点之间会选举出一个节点作为主节点

![image-20240317211745166](C:\Users\LYS\AppData\Roaming\Typora\typora-user-images\image-20240317211745166.png)

****

### 服务监控原理

****

![image-20240317211956994](https://image.itbaima.cn/images/40/image-20240317219787913.png)

- Sentinel 基于心跳机制监控服务状态，每 1 s 向集群的每个实例发送一次 ping
- 主观下线：某个 Sentinel 节点发现某个实例未响应，认为该实例主观下线
- 客观下线：超过一定数量的 Sentinel 节点都认为该实例主观下线，则该实例客观下线

****

### 选举规则

****

**复制偏移量**：

- 也被称为复制积压缓冲区（Replication Backlog）中的偏移量，用于记录主从节点之间的数据同步情况
- 主节点在处理每一条命令后，会生成一条带有相应偏移量的命令日志，并将这个日志发送给所有的从节点
- 主节点也会在本地维护一个复制积压缓冲区（repl_backlog ），存储最近的命令日志，复制偏移量实际上就是这个复制积压缓冲区的尾部的偏移位置

具体选举规则如下：

- 首先判断与主节点断开时间最短的从节点，
- 然后判断从节点的 slave-priority 值，值越小优先级越高
- slave-priority 值相同判断复制偏移量（offset）的值，值越大优先级越高
- 最后是从节点 runid，runid越小优先级越高

****

### 脑裂问题

****

假设 Sentinel 和 集群的各个实例处于不同的网络分区，由于网络抖动，Sentinel 没有心跳感知到主节点，因此选举提升了一个从节点作为新的主节点：

- 客户端由于还在老的主节点写数据
- 但网络恢复后，老的主节点会被强制降为从节点导致原有数据丢失

**解决方案**：

- 设置 redis 参数
- min-replicas-to-write 1 表示最少的 salve 节点为 1 个
- min-replicas-max-lag 5 表示数据复制和同步的延迟不能超过 5 秒
- 如果发生脑裂，原master会在客户端写入操作的时候拒绝请求，避免数据大量丢失

****

# Redis Cluster 解决方案

****

## 基础概念

****

首先，分析一下主从+哨兵模式带来的问题：

![image-20240318202940569](https://image.itbaima.cn/images/40/image-20240318202378518.png)

- 在主从 + 哨兵的模式下，仍然只有一个 Master 节点，当并发请求较大时，哨兵模式不能缓解写压力
- 在 Sentinel 模式下，每个节点需要保存全量数据，无法进行海量数据存储

因此，在 Redis 3.0 之后，提供了 Cluster  的解决方案，核心原理是对数据做分片：

![image-20240318203511203](https://image.itbaima.cn/images/40/image-20240318202255799.png)

- 采用无中心结构
- 每个 master 可以有多个 slave 节点
- 整个集群分片共有 16384 个哈希槽
- 每个 key 通过 CRC16 校验后对 16384 取模来决定放置哪个槽，集群的每个节点负责一部分hash 槽
- 当主节点不可用时，从节点会升级为主节点，原有主节点恢复后会降级为从节点

****

## Redis Cluster 集群策略

****

### 故障转移策略

****

![image-20240318204921709](https://image.itbaima.cn/images/40/image-20240318201010339.png)

和 Sentinel 类似，Cluster 也存在服务监控和选举规则：

- 主观下线：和 Sentinel 一样采用心跳包检测，当一个节点不能从另一个节点接收到心跳信息，该节点会将它标记为“主观下线”状态
- 客观下线：当半数以上的主节点都将某个节点标记为“主观下线”，那么这个节点会被标记为“客观下线”

当某个节点被标记为客观下线后，会从该主节点的从节点中选举一个从节点作为新的主节点：

- 选举过程主要看从节点的复制偏移量（replica offset）和 runid
- 优先选择复制偏移量最大的节点，如果复制偏移量相同，则选择 runid 最小的节点

**注意**：

- 若某一主节点及其从节点都不可用，则会导致整个 Redis Cluster 集群不可用

****

### 数据分片策略

****

#### 常见的数据分布策略

****

**顺序分布**：

- 根据数据的某些属性进行排序，将数据均匀地分配到不同的存储节点
- 例如，将用户 ID 排序，分区间存入不同的节点

**一致性哈希**：

- 将整个哈希值空间组成一个虚拟的圆环，然后根据某种哈希算法将数据项映射到该圆环上
- 例如对于 Redis，对节点 id 进行 hash，将其值分布在圆环上
- 发生读写的 key 经过 hash 后，顺时针查圆环上的节点，若未找到，则默认为 0 位置后的第一个节点

如果采用一致性哈希算法，若某个节点挂了，受影响的数据仅仅是此节点到环空间前一个节点（沿着逆时针方向行走遇到的第一个节点）之间的数据，其它不受影响。增加一个节点也同理。

但是当删除节点时，数据再分配会把当前节点所有数据加到它的下一个节点上（缓存抖动）。这样会导致下一个节点使用率暴增，可能会导致挂掉，如果下一个节点挂掉，下下个节点将会承受更大的压力，最终导致集群雪崩。

****

#### Redis 哈希槽策略

****

Redis 并没有使用一致性哈希，而是采用哈希槽的方式进行分片

Redis 集群有16384个哈希槽，每个key通过CRC16校验后对16384取模来决定放置哪个槽：

![image-20240318215405104](https://image.itbaima.cn/images/40/image-20240318218022338.png)

> 理论上 CRC16 算法可以得到 $2^{16}$ 个数值，其数值范围在 0-65535 之间，取模运算 key 的时候，应该是CRC16(key)%65535，但是却设计为CRC16(key)%16384，原因是作者在设计的时候做了空间上的权衡，觉得节点最多不可能超过1000个，同时为了保证节点之间通信效率，所以采用了 $2^{14}$。

具体分片方式如下：

- 把16384槽按照节点数量进行平均分配，由节点进行管理
- 对每个key按照 CRC16规则进行 hash 运算
- 把hash结果对 16383 进行取余
- 把余数发送给 Redis 节点
- 节点接收到数据，验证是否在自己管理的槽编号的范围
  - 如果在自己的编号范围内，会把数据存储到数据槽中，返回执行结果
  - 否则，会把数据发送给正确的节点，由正确的节点来处理

**使用哈希槽的优势**：

- 由于一致性哈希会造成缓存抖动和集群雪崩，因此要在原有基础上进行扩容和删减节点变得极为困难
- 使用哈希槽在新增节点时，只需要将其他节点的哈希槽分出一部分给新节点
- 删除节点时，则将该节点的哈希槽再分配给别的节点，之后再删除节点即可

**注意**：

- Redis Cluster 节点之间共享消息，每个节点会知道哪个节点负责哪个数据槽
- 添加节点后，需要手动给新节点分配哈希槽，从其他节点的哈希槽分来一部分，并且支持哈希槽均衡

****

# 分布式锁

****

本章节的 demo 代码示例，免搭建即开即用：**[learn-redis-demo](https://github.com/Doge2077/learn-redis-demo)**

****

## 基于 Redis 实现分布式锁

****

### 基础实现

****

基于 Redis 实现分布式锁主要依赖于 `SETNX` 命令：

- `SETNX key value`：若不存在 key 则设置 key 值为 value，返回 1
- 若 key 已存在，则不做任何操作，返回 0

为了防止某个线程获取锁之后异常结束没有释放锁，导致其他线程调用 `SETNX` 命令返回 0 而进入死锁，因此加锁后需要设置超时时间

以下是一个简单的 SpringBoot demo：

```java
@RestController
@RequestMapping("/sell")
public class AppController {
    @Resource
    StringRedisTemplate stringRedisTemplate;

    String LOCK = "TICKETSELLER";
    String KEY = "TICKET";

    @GetMapping("/ticket")
    public void sellTicket() {
        Boolean isLocked = stringRedisTemplate.opsForValue().setIfAbsent(LOCK, "1");
        if (Boolean.TRUE.equals(isLocked)) {
            // 设置过期时间 5s
            stringRedisTemplate.expire(LOCK, 5, TimeUnit.SECONDS);
            try {
                // 拿到 ticket 的数量
                int ticketCount = Integer.parseInt((String) stringRedisTemplate.opsForValue().get(KEY));
                if (ticketCount > 0) {
                    // 扣减库存
                    stringRedisTemplate.opsForValue().set(KEY, String.valueOf(ticketCount - 1));
                    System.out.println("I get a ticket!");
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                // 释放锁
                stringRedisTemplate.delete(LOCK);
            }
        } else {
            System.out.println("Field");
        }
    }

}
```

****

### 缺陷分析

****

#### 加锁和设置过期时间非原子操作

****

- 我们先是用 `SETNX` 创建了锁，假如这个服务在创建锁之后由于事故导致直接停机，那么这个锁就是一个永不过期的锁
- 这将导致其他服务无法获取到锁，影响业务的正常进行

解决方案：

- 使用 LUA  脚本来进行加锁和设置过期时间的操作
- 这样可以使得加锁和设置过期时间是一个原子操作

```java
@RestController
@RequestMapping("/sell")
public class AppController {
    @Resource
    StringRedisTemplate stringRedisTemplate;

    String LOCK = "TICKETSELLER";
    String KEY = "TICKET";

    @GetMapping("/ticket")
    public void sellTicket() {
        // LUA  脚本
        String LUA Script =
                "if redis.call('setnx',KEYS[1],ARGV[1]) == 1 " +
                        "then redis.call('expire',KEYS[1],ARGV[2]) ;" +
                        "return true " +
                "else return false " +
                "end";
        
        // 回调函数返回加锁状态
        Boolean isLocked = stringRedisTemplate.execute(new RedisCallback<Boolean>() {
            @Override
            public Boolean doInRedis(RedisConnection connection) throws DataAccessException {
               return connection.eval(LUA Script.getBytes(),
                        ReturnType.BOOLEAN,
                        1,
                        LOCK.getBytes(),
                        "1".getBytes(),
                        "5".getBytes());
            }
        });
        if (Boolean.TRUE.equals(isLocked)) {
            try {
                int ticketCount = Integer.parseInt((String) stringRedisTemplate.opsForValue().get(KEY));
                if (ticketCount > 0) {
                    stringRedisTemplate.opsForValue().set(KEY, String.valueOf(ticketCount - 1));
                    System.out.println("I get a ticket!");
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                stringRedisTemplate.delete(LOCK);
            }
        } else {
            System.out.println("Field");
        }
    }

}
```

****

#### 锁的过期时间设置是否合理

****

![](https://image.itbaima.cn/images/40/image-20240319003866632.png)

假设现有服务 A 和服务 B，A 先拿到锁执行业务，但是由于业务过长导致 A 的锁到期后超时释放：

- 如果 B 的业务还没结束，A 的业务结束进行释放锁的操作，A 就会错误的删除掉 B 加的锁，那 B 的业务执行完就无锁可释了
- 如果 B 服务可以获取到锁了，B 加锁并执行他的业务，由于此时 A 也在执行业务，两个服务共享内存就容易造成超卖问题

针对第一种问题的出现，解决方案很简单，只需要对锁的值做出限制即可：

- 设置加锁 key 的值为唯一，如利用 uid + threadid
- 在释放锁时判断是否是自己的锁，如果是则释放
- 这个释放锁的操作也要保证原子性，因此也需要用 LUA 脚本来实现

```java
@RestController
@RequestMapping("/sell")
public class AppController {
    @Resource
    StringRedisTemplate stringRedisTemplate;

    String LOCK = "TICKETSELLER";
    String KEY = "TICKET";       // 记得在 redis 里面设置好 TICKET 的数量

    @GetMapping("/ticket")
    public void sellTicket() {
        String lockLuaScript =
                "if redis.call('setnx',KEYS[1],ARGV[1]) == 1 " +
                        "then redis.call('expire',KEYS[1],ARGV[2]) ;" +
                        "return true " +
                        "else return false " +
                        "end";

        // 生产环境替换为 uuid + 线程 id
        String VALUE = String.valueOf(Thread.currentThread().getId());
        Boolean isLocked = stringRedisTemplate.execute(new RedisCallback<Boolean>() {
            @Override
            public Boolean doInRedis(RedisConnection connection) throws DataAccessException {
                return connection.eval(lockLuaScript.getBytes(),
                        ReturnType.BOOLEAN,
                        1,
                        LOCK.getBytes(),
                        VALUE.getBytes(),  // 用于判断是否为当前线程加的锁
                        "5".getBytes()
                );
            }
        });
        if (Boolean.TRUE.equals(isLocked)) {
            try {
                int ticketCount = Integer.parseInt((String) stringRedisTemplate.opsForValue().get(KEY));
                if (ticketCount > 0) {
                    stringRedisTemplate.opsForValue().set(KEY, String.valueOf(ticketCount - 1));
                    System.out.println("I get a ticket!");
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
//                // 判断是否是自己加的锁，如果是则释放 缺点：非原子操作
//                String LOCK_ID = stringRedisTemplate.opsForValue().get(LOCK);
//                if (LOCK_ID != null && LOCK_ID.equals(VALUE)) {
//                    stringRedisTemplate.delete(LOCK);
//                }
                String unlockLuaScript =
                        "if redis.call('get',KEYS[1]) == ARGV[1] " +
                                "then redis.call('del',KEYS[1]); " +
                                "return true " +
                                "else return false " +
                                "end";
                stringRedisTemplate.execute(new RedisCallback<Object>() {
                    @Override
                    public Object doInRedis(RedisConnection connection) throws DataAccessException {
                        return connection.eval(unlockLuaScript.getBytes(),
                                ReturnType.BOOLEAN,
                                1,
                                LOCK.getBytes(),
                                VALUE.getBytes()
                        );
                    }
                });
            }
        } else {
            System.out.println("Field");
        }
    }

}
```

针对第二种问题，我们可以利用看门狗机制实现：

- 开一个守护线程，每隔一段时间就获取一次锁的状态
- 如果仍然持有锁，则对其续期，此过程仍然利用 LUA 脚本实现
- 当业务结束后终止该线程

```java
@RestController
@RequestMapping("/sell")
public class AppController {
    @Resource
    StringRedisTemplate stringRedisTemplate;

    String LOCK = "TICKETSELLER";
    String KEY = "TICKET";       // 记得在 redis 里面设置好 TICKET 的数量

    @GetMapping("/ticket")
    public void sellTicket() {
        String lockLuaScript =
                "if redis.call('setnx',KEYS[1],ARGV[1]) == 1 " +
                        "then redis.call('expire',KEYS[1],ARGV[2]) ;" +
                        "return true " +
                        "else return false " +
                        "end";
        // 生产环境替换为 uuid + 线程 id
        String VALUE = String.valueOf(Thread.currentThread().getId());
        Boolean isLocked = stringRedisTemplate.execute(new RedisCallback<Boolean>() {
            @Override
            public Boolean doInRedis(RedisConnection connection) throws DataAccessException {
                return connection.eval(lockLuaScript.getBytes(),
                        ReturnType.BOOLEAN,
                        1,
                        LOCK.getBytes(),
                        VALUE.getBytes(),  // 用于判断是否为当前线程加的锁
                        "5".getBytes()
                );
            }
        });
        if (Boolean.TRUE.equals(isLocked)) {
            // 判断是否是自己加的锁，如果是则续期
            String addlockLuaScript =
                    "if redis.call('get',KEYS[1]) == ARGV[1] " +
                            "then redis.call('expire',KEYS[1], ARGV[2]) ; " +
                            "return true " +
                            "else return false " +
                            "end";
            Thread watchDoge = new Thread(() -> {
                while (Boolean.TRUE.equals(stringRedisTemplate.execute(new RedisCallback<Boolean>() {
                    @Override
                    public Boolean doInRedis(RedisConnection connection) throws DataAccessException {
                        return connection.eval(addlockLuaScript.getBytes(),
                                ReturnType.BOOLEAN,
                                1,
                                LOCK.getBytes(),
                                VALUE.getBytes(),
                                "5".getBytes());
                    }
                })) && !Thread.currentThread().isInterrupted()) {
                    try {
                        System.out.println(Thread.currentThread().isInterrupted());
                        Thread.sleep(4000);
                    } catch (Exception e) {
                        break;
                    }
                }
            });
            watchDoge.setDaemon(true);
            watchDoge.start();
            try {
                int ticketCount = Integer.parseInt((String) stringRedisTemplate.opsForValue().get(KEY));
                if (ticketCount > 0) {
                    stringRedisTemplate.opsForValue().set(KEY, String.valueOf(ticketCount - 1));
//                    Thread.sleep(10000000);  // 在这里睡一下，可以到 redis 里面 TTL TICKETSELLER 查看锁是否被续期
                    watchDoge.interrupt();
                    System.out.println("I get a ticket!");
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                String unlockLuaScript =
                        "if redis.call('get',KEYS[1]) == ARGV[1] " +
                                "then redis.call('del',KEYS[1]); " +
                                "return true " +
                                "else return false " +
                                "end";
                stringRedisTemplate.execute(new RedisCallback<Object>() {
                    @Override
                    public Object doInRedis(RedisConnection connection) throws DataAccessException {
                        return connection.eval(unlockLuaScript.getBytes(),
                                ReturnType.BOOLEAN,
                                1,
                                LOCK.getBytes(),
                                VALUE.getBytes()
                        );
                    }
                });
            }
        } else {
            System.out.println("Field");
        }
    }

}
```

****

#### 其他缺陷

****

对于上面的看门狗机制，其实是一个极其朴素的实现，实际上需要考虑到的东西还有很多。

另外上述的实现仍缺少一些高级应用场景的功能：

- 如何实现锁的可重入：增加重入次数的参数，实现锁的成对加锁和释放。
- 如何实现阻塞的锁：客户端轮询（性能开销大）或者发布订阅

而这些功能想要自己去实现是非常麻烦的，因此一般利用 Redisson 实现分布式锁。

****

## 基于 Redisson 实现分布式锁

****

### 基础操作

****

Redisson 内置了一系列的分布式对象，分式集合，分布式锁，分布式服务等诸多功能特性，是一款基于 Redis 实现，拥有一系列分布式
系统功能特性的工具包，是实现分布式系统架构中缓存中间件的最佳选择。

引入依赖：

```xml
<dependency>
	<groupId>org.redisson</groupId>
	<artifactId>redisson</artifactId>
	<version>3.27.2</version>
</dependency>
```

编写 Redisson 配置类：

```java
@Configuration
public class RedissonConfig {
    // 构建 Redisson 客户端配置
    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer().setAddress("redis://127.0.0.1:6379");
        return Redisson.create(config);
    }
}
```

注入到 Controller：

```java
@RestController
@RequestMapping("/redisson")
public class RedissonAppController {

    String LOCK = "REIDSSON:TICKETSELLER";
    String KEY = "TICKET";

    // 注入
    @Resource
    RedissonClient redissonClient;

    @Resource
    StringRedisTemplate stringRedisTemplate;

    @GetMapping("/sell/ticket")
    public void redissonSellTicket() {
    	// 加锁
        RLock rLock = redissonClient.getLock(LOCK);
        rLock.lock();
        try {
            int count = Integer.parseInt((String) stringRedisTemplate.opsForValue().get(KEY));
            if (count > 0) {
                stringRedisTemplate.opsForValue().set(KEY, String.valueOf(count - 1));
                System.out.println("Reidsson get ticket");
            } else {
                System.out.println("Field");
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
        	// 释放锁
            rLock.unlock();
        }
    }

}
```

****

### 源码剖析

****

#### 加锁原理

****

首先来看 `package org.redisson` 包下的 `lock` 方法的具体实现：

```java
private void lock(long leaseTime, TimeUnit unit, boolean interruptibly) throws InterruptedException {
    long threadId = Thread.currentThread().getId();
    /*
     * 这里调用 tryAcquire 尝试获取锁
     *    如果为 null 说明获取到了锁
     *    如果不是 null 说明其他线程持有锁
     * 这个方法最底层的实现其实也是 LUA 脚本
     */
    Long ttl = this.tryAcquire(-1L, leaseTime, unit, threadId);
    if (ttl != null) {
        // 发布订阅，非阻塞锁
        CompletableFuture<RedissonLockEntry> future = this.subscribe(threadId);
        this.pubSub.timeout(future);
        RedissonLockEntry entry;
        if (interruptibly) {
            entry = (RedissonLockEntry)this.commandExecutor.getInterrupted(future);
        } else {
            entry = (RedissonLockEntry)this.commandExecutor.get(future);
        }

        try {
            while(true) {
                // 仍然尝试获取锁
                ttl = this.tryAcquire(-1L, leaseTime, unit, threadId);
                if (ttl == null) {
                    return;
                }

                if (ttl >= 0L) {
                    try {
                        entry.getLatch().tryAcquire(ttl, TimeUnit.MILLISECONDS);
                    } catch (InterruptedException var14) {
                        if (interruptibly) {
                            throw var14;
                        }

                        entry.getLatch().tryAcquire(ttl, TimeUnit.MILLISECONDS);
                    }
                } else if (interruptibly) {
                    entry.getLatch().acquire();
                } else {
                    entry.getLatch().acquireUninterruptibly();
                }
            }
        } finally {
            // 取消订阅频道
            this.unsubscribe(entry, threadId);
        }
    }
}
```

接下来我们看 `tryAcquire` 尝试获取锁的方法 `tryAcquireOnceAsync`：

```java
private RFuture<Boolean> tryAcquireOnceAsync(long waitTime, long leaseTime, TimeUnit unit, long threadId) {
        RFuture acquiredFuture;
        if (leaseTime > 0L) {
            acquiredFuture = this.tryLockInnerAsync(waitTime, leaseTime, unit, threadId, RedisCommands.EVAL_NULL_BOOLEAN);
        } else {
            // 未设定过期时间走这个默认的
            acquiredFuture = this.tryLockInnerAsync(waitTime, this.internalLockLeaseTime, TimeUnit.MILLISECONDS, threadId, RedisCommands.EVAL_NULL_BOOLEAN);
        }

        CompletionStage<Boolean> acquiredFuture = this.handleNoSync(threadId, acquiredFuture);
        CompletionStage<Boolean> f = acquiredFuture.thenApply((acquired) -> {
            if (acquired) {
                if (leaseTime > 0L) {
                    this.internalLockLeaseTime = unit.toMillis(leaseTime);
                } else {
                    this.scheduleExpirationRenewal(threadId);
                }
            }

            return acquired;
        });
        return new CompletableFutureWrapper(f);
    }
```

可以看到 `tryLockInnerAsync` 传参中多了一个参数 `this.internalLockLeaseTime`，这个东西的初始化在：

```
public RedissonLock(CommandAsyncExecutor commandExecutor, String name) {
        super(commandExecutor, name);
        this.commandExecutor = commandExecutor;
        // 看门狗机制的续期时间
        this.internalLockLeaseTime = this.getServiceManager().getCfg().getLockWatchdogTimeout();
        this.pubSub = commandExecutor.getConnectionManager().getSubscribeService().getLockPubSub();
}
```

这个续期时间的默认值可以在 Config 里面找到：

```java
    public Config() {
        this.transportMode = TransportMode.NIO;
        // 默认是 30s
        this.lockWatchdogTimeout = 30000L;
        this.checkLockSyncedSlaves = true;
        this.slavesSyncTimeout = 1000L;
        this.reliableTopicWatchdogTimeout = TimeUnit.MINUTES.toMillis(10L);
        this.keepPubSubOrder = true;
        this.useScriptCache = false;
        this.minCleanUpDelay = 5;
        this.maxCleanUpDelay = 1800;
        this.cleanUpKeysAmount = 100;
        this.nettyHook = new DefaultNettyHook();
        this.useThreadClassLoader = true;
        this.addressResolverGroupFactory = new SequentialDnsAddressResolverFactory();
        this.protocol = Protocol.RESP2;
    }
```

最后我们回到最底层的 `tryLockInnerAsync` 方法：

```java
<T> RFuture<T> tryLockInnerAsync(long waitTime, long leaseTime, TimeUnit unit, long threadId, RedisStrictCommand<T> command) {
        return this.evalWriteSyncedAsync(this.getRawName(), LongCodec.INSTANCE, command, "if ((redis.call('exists', KEYS[1]) == 0) or (redis.call('hexists', KEYS[1], ARGV[2]) == 1)) then redis.call('hincrby', KEYS[1], ARGV[2], 1); redis.call('pexpire', KEYS[1], ARGV[1]); return nil; end; return redis.call('pttl', KEYS[1]);", Collections.singletonList(this.getRawName()), new Object[]{unit.toMillis(leaseTime), this.getLockName(threadId)});
}
```

这里实际执行的是一个 LUA 脚本：

```lua
-- 判断是否存在 KEY，不存在则加锁
if (redis.call('exists', KEYS[1]) == 0) or (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then
    redis.call('hincrby', KEYS[1], ARGV[2], 1);  -- 对 hash 的字段加一
    redis.call('pexpire', KEYS[1], ARGV[1]);     -- 设置过期时间
    return nil;
else
    return redis.call('pttl', KEYS[1]); -- 存在锁说明其他线程占有，返回过期时间
end;
```

这里新版的 Redisson 加锁的逻辑简化了，以前是区分了加锁和可重入，现在进行了合并。

****

#### 看门狗机制原理

****

继续看 `tryAcquireAsync` 方法，在获取到锁后，走 `scheduleExpirationRenewal` 的逻辑：

```java
private RFuture<Long> tryAcquireAsync(long waitTime, long leaseTime, TimeUnit unit, long threadId) {
    RFuture ttlRemainingFuture;
    if (leaseTime > 0L) {
        ttlRemainingFuture = this.tryLockInnerAsync(waitTime, leaseTime, unit, threadId, RedisCommands.EVAL_LONG);
    } else {
        ttlRemainingFuture = this.tryLockInnerAsync(waitTime, this.internalLockLeaseTime, TimeUnit.MILLISECONDS, threadId, RedisCommands.EVAL_LONG);
    }

    CompletionStage<Long> s = this.handleNoSync(threadId, ttlRemainingFuture);
    RFuture<Long> ttlRemainingFuture = new CompletableFutureWrapper(s);
    CompletionStage<Long> f = ttlRemainingFuture.thenApply((ttlRemaining) -> {
        if (ttlRemaining == null) {
            if (leaseTime > 0L) {
                this.internalLockLeaseTime = unit.toMillis(leaseTime);
            } else {
                this.scheduleExpirationRenewal(threadId);  // 锁续期
            }
        }

        return ttlRemaining;
    });
    return new CompletableFutureWrapper(f);
}
```

点进去看 `scheduleExpirationRenewal` 方法：

```java
protected void scheduleExpirationRenewal(long threadId) {
        ExpirationEntry entry = new ExpirationEntry();
        ExpirationEntry oldEntry = (ExpirationEntry)EXPIRATION_RENEWAL_MAP.putIfAbsent(this.getEntryName(), entry);
        if (oldEntry != null) {
            oldEntry.addThreadId(threadId);
        } else {
            entry.addThreadId(threadId);

            try {
                this.renewExpiration();  // 创建定时任务
            } finally {
                if (Thread.currentThread().isInterrupted()) {
                    this.cancelExpirationRenewal(threadId, (Boolean)null);
                }

            }
        }

    }
```

创建定时任务的逻辑：

```java
private void renewExpiration() {
        ExpirationEntry ee = (ExpirationEntry)EXPIRATION_RENEWAL_MAP.get(this.getEntryName());
        if (ee != null) {
            Timeout task = this.getServiceManager().newTimeout(new TimerTask() {
                public void run(Timeout timeout) throws Exception {
                    ExpirationEntry ent = (ExpirationEntry)RedissonBaseLock.EXPIRATION_RENEWAL_MAP.get(RedissonBaseLock.this.getEntryName());
                    if (ent != null) {
                        Long threadId = ent.getFirstThreadId();
                        if (threadId != null) {
                            CompletionStage<Boolean> future = RedissonBaseLock.this.renewExpirationAsync(threadId);
                            future.whenComplete((res, e) -> {
                                if (e != null) {
                                    RedissonBaseLock.log.error("Can't update lock {} expiration", RedissonBaseLock.this.getRawName(), e);
                                    RedissonBaseLock.EXPIRATION_RENEWAL_MAP.remove(RedissonBaseLock.this.getEntryName());
                                } else {
                                    if (res) {
                                        RedissonBaseLock.this.renewExpiration();
                                    } else {
                                        RedissonBaseLock.this.cancelExpirationRenewal((Long)null, (Boolean)null);
                                    }

                                }
                            });
                        }
                    }
                }
            }, this.internalLockLeaseTime / 3L, TimeUnit.MILLISECONDS);  // 这个值在之前讲过，续期用的，默认为 30s，因此这个任务默认每隔 10s 执行一次
            ee.setTimeout(task);
        }
    }
```

每次定时任务触发，会执行 `renewExpirationAsync` 方法：

```java
protected CompletionStage<Boolean> renewExpirationAsync(long threadId) {
        return this.evalWriteSyncedAsync(this.getRawName(), LongCodec.INSTANCE, RedisCommands.EVAL_BOOLEAN, "if (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then redis.call('pexpire', KEYS[1], ARGV[1]); return 1; end; return 0;", Collections.singletonList(this.getRawName()), this.internalLockLeaseTime, this.getLockName(threadId));
}
```

可以看到，本质仍然是一个 LUA 脚本：

```lua
-- 检查 KEY 是否存在
if (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then 
	redis.call('pexpire', KEYS[1], ARGV[1]);  -- 存在则更新过期时间为 this.internalLockLeaseTime，就是默认那 30s
	return 1; -- 成功返回
end; 
return 0;
```

****

#### 解锁原理

****

首先来看 `package org.redisson` 包下的 `unlock` 方法的具体实现：

```java
public void unlock() {
        try {
            this.get(this.unlockAsync(Thread.currentThread().getId()));
        } catch (RedisException var2) {
            if (var2.getCause() instanceof IllegalMonitorStateException) {
                throw (IllegalMonitorStateException)var2.getCause();
            } else {
                throw var2;
            }
        }
    }
```

调用了方法 `unlockAsync`：

```java
public RFuture<Void> unlockAsync(long threadId) {
        return this.getServiceManager().execute(() -> {
            return this.unlockAsync0(threadId);
        });
    }

// 又调用了这段
private RFuture<Void> unlockAsync0(long threadId) {
        CompletionStage<Boolean> future = this.unlockInnerAsync(threadId);
        CompletionStage<Void> f = future.handle((res, e) -> {
            this.cancelExpirationRenewal(threadId, res);
            if (e != null) {
                if (e instanceof CompletionException) {
                    throw (CompletionException)e;
                } else {
                    throw new CompletionException(e);
                }
            } else if (res == null) {
                IllegalMonitorStateException cause = new IllegalMonitorStateException("attempt to unlock lock, not locked by current thread by node id: " + this.id + " thread-id: " + threadId);
                throw new CompletionException(cause);
            } else {
                return null;
            }
        });
        return new CompletableFutureWrapper(f);
    }
```

接下来走 `unlockInnerAsync` 的逻辑：

```java
protected final RFuture<Boolean> unlockInnerAsync(long threadId) {
    // 生成一个会话ID用于锁的释放
    String id = this.getServiceManager().generateId();
    
    // 获取Redisson的配置对象
    MasterSlaveServersConfig config = this.getServiceManager().getConfig();
    
    // 计算超时的时间，这是基于配置中的超时时间、重试间隔和重试次数计算出的总时间
    int timeout = (config.getTimeout() + config.getRetryInterval()) * config.getRetryAttempts();
    timeout = Math.max(timeout, 1);
    
    // 执行异步任务以释放锁
    RFuture<Boolean> r = this.unlockInnerAsync(threadId, id, timeout);
    
    // 使用CompletionStage处理异步操作的结果
    CompletionStage<Boolean> ff = r.thenApply((v) -> {
        CommandAsyncExecutor ce = this.commandExecutor;
        
        // 判断commandExecutor是否是CommandBatchService的一个实例
        if (ce instanceof CommandBatchService) {
            // 如果是，创建一个新的CommandBatchService实例
            ce = new CommandBatchService(this.commandExecutor);
        }

        // 执行DEL命令以删除锁相关的数据
        ((CommandAsyncExecutor)ce).writeAsync(this.getRawName(), 
                                              LongCodec.INSTANCE, 
                                              RedisCommands.DEL, 
                                              new Object[]{this.getUnlockLatchName(id)});
        
        // 如果为CommandBatchService实例，则执行异步批量提交操作
        if (ce instanceof CommandBatchService) {
            ((CommandBatchService)ce).executeAsync();
        }

        // 返回之前的异步任务的结果
        return v;
    });

    // 将CompletionStage的执行结果包装为RFuture返回
    return new CompletableFutureWrapper(ff);
}
```

重点在于执行异步任务释放锁的过程：

```java
protected RFuture<Boolean> unlockInnerAsync(long threadId, String requestId, int timeout) {
        return this.evalWriteSyncedAsync(this.getRawName(), LongCodec.INSTANCE, RedisCommands.EVAL_BOOLEAN, "local val = redis.call('get', KEYS[3]); if val ~= false then return tonumber(val);end; if (redis.call('hexists', KEYS[1], ARGV[3]) == 0) then return nil;end; local counter = redis.call('hincrby', KEYS[1], ARGV[3], -1); if (counter > 0) then redis.call('pexpire', KEYS[1], ARGV[2]); redis.call('set', KEYS[3], 0, 'px', ARGV[5]); return 0; else redis.call('del', KEYS[1]); redis.call(ARGV[4], KEYS[2], ARGV[1]); redis.call('set', KEYS[3], 1, 'px', ARGV[5]); return 1; end; ", Arrays.asList(this.getRawName(), this.getChannelName(), this.getUnlockLatchName(requestId)), new Object[]{LockPubSub.UNLOCK_MESSAGE, this.internalLockLeaseTime, this.getLockName(threadId), this.getSubscribeService().getPublishCommand(), timeout});
}
```

可以看到，本质还是一个 LUA 脚本：

```lua
-- 尝试从KEYS[3]获取值
local val = redis.call('get', KEYS[3])
-- 如果val不为false，则返回它的数字表示
if val ~= false then
    return tonumber(val)
end
-- 检查hash KEYS[1]中是否存在字段ARGV[3]
if (redis.call('hexists', KEYS[1], ARGV[3]) == 0) then
    -- 如果不存在，则返回nil
    return nil
end
-- 在hash KEYS[1]里将字段ARGV[3]的值减1，并将结果保存在counter中
local counter = redis.call('hincrby', KEYS[1], ARGV[3], -1)
-- 如果计数器仍然大于0
if (counter > 0) then
    -- 设置hash KEYS[1]的过期时间为ARGV[2]毫秒
    redis.call('pexpire', KEYS[1], ARGV[2])
    -- 设置KEYS[3]的值为0，并设置过期时间为ARGV[5]毫秒
    redis.call('set', KEYS[3], 0, 'px', ARGV[5])
    return 0
else
    -- 如果计数器不大于0，则删除hash KEYS[1]
    redis.call('del', KEYS[1])
    -- 执行ARGV[4]（可能是发布某些消息）到KEYS[2]
    redis.call(ARGV[4], KEYS[2], ARGV[1])
    -- 设置KEYS[3]的值为1，并设置过期时间为ARGV[5]毫秒
    redis.call('set', KEYS[3], 1, 'px', ARGV[5])
    return 1
end
```

****

# 三大使用陷阱

****

## 缓存穿透

****

### 原因分析

****

- 查询到的 key 不存在导致查询结果没有写入缓存
- 后续大量这样的请求直接打到数据库压力很大

这里主要是很多这种的请求打过来，查到的 key 不存在的次数较多，导致数据库压力倍增

****

### 解决方案

****

较为简单的解决方案是将这种查询不到的 key 设置为空值缓存并返回，缺点是占内存，实际上可以采用更加优雅的解决方案——添加布隆过滤器：

- 一个 bitmap，多个 hash 函数
- 对于已经缓存的 key，经过多次 hash 在 bitmap 中做映射
- 如果请求的 key 多次映射后全部命中，则说明在 Redis 中**可能**存在，放行请求
- 否则拒绝请求

![image-20240320175505310](https://image.itbaima.cn/images/40/image-20240320174074053.png)

这里全部命中后的“可能”存在是因为存在哈希冲突的可能性：

- 假设已经存在缓存中的 x, y, z 这三个 key 做 hash 后命中的 bitmap 如上图所示
- 现在有 w 这个 key 请求打过来，多次 hash 后发现全部命中，这就造成了误判

技术上实现：

- 本地缓存：Caffine 或者 Guava
- 基于 Redisson 实现

****

## 缓存击穿

****

### 原因分析

****

- 对于设置了过期时间的 key，缓存在某个时间点过期的时出现大量高并发请求
- 请求发现缓存过期会从后端 DB 加载数据并写回到缓存，这个时候大并发的请求可能会瞬间把 DB 压垮

这里主要是针对某个 key 的，某个 key 恰好过期恰好大量请求打到这个 key 上

****

### 解决方案

****

![image-20240320181549116](https://image.itbaima.cn/images/40/image-20240320182318621.png)

- 使用互斥锁：
  - 缓存失效时不立即查询 DB
  - 先用 redis 的 setnx 设置互斥锁
  - 成功返回再查询 DB 并写回缓存，否则重试 get 缓存方法
  - 能保证强一致性，但线程需要等待有死锁风险
- 设置 key 逻辑过期：
  - 设置 key 时添加一个字段表示过期时间，然后设置永不过期
  - 查询到该 key 比对过期时间判断是否过期
  - 如果过期新开线程进行数据同步，当前线程正常返回数据，但数据不是最新的
  - 不能保证一致性，但线程无需等待

****

## 缓存雪崩

****

### 原因分析

****

- 大量设置缓存时间相同的 key 在同一时间大量失效
- 导致很多失效的 key 全部查询 DB

这里算是缓存击穿的升级版，大量的同一过期时间的 key 失效，结果大量请求过来，虽然查询的不是同一个 key，但未命中的流量占大部分

****

### 解决方案

****

- 将缓存失效时间分散，在原有时间上设置随机数错开失效时间
- 采用加锁计数，或者使用合理的队列数量来避免缓存失效时对数据库造成太大的压力，但是会降低系统的吞吐量
- 分析用户行为，尽量让失效时间点均匀分布，尽量避免缓存雪崩的出现

****





















