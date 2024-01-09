# Redis 应用与原理（一）

****

## 缓存发展史

****

### 缓存经典场景

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

#### 三大经典缓存读写策略

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

#### 双写一致性解决方案

****

以上三种经典的读写策略在一定条件下都会产生缓存和数据库数据不一致的问题，这里给出两种解决方案

**同步方案**：

- 延迟双删：更新数据时先删除缓存，然后修改数据库，延迟一段时间后再次删除缓存
- 延迟一段时间是为了保证数据库集群下的数据同步

**异步方案**：

- 使用消息队列：更改代码加入异步操作缓存的逻辑代码，数据库操作完毕后将要同步的数据发给 mq，mq 的消费者从 mq 获取数据更新缓存
- 使用 canal 组件实现同步：不需要更改业务代码，只需要部署一个 canal 服务，canal 把自己伪装为了 mysql 的从节点，canal 读取 binlog 日志更新缓存

****

### 分布式缓存方案选型

****

分布式缓存主要解决的是单机缓存的容量受服务器限制并且无法保存通用的信息。

因为，本地缓存只在当前服务里有效，部署两个相同的服务，他们两者之间的本地缓存数据无法共通。

常见的分布式缓存方案为：

- Redis
- Memcache
- Tair

****

#### Redis 和 Memcache 对比

****

**共同点**：

- 都是基于内存的数据库，一般都用来当做缓存使用
- 都有过期策略

**区别**：

- Redis 支持的数据类型更丰富，而 Memcached 只支持最简单的 key-value 数据类型
- Redis 支持数据持久化，有 RDB 和 AOF 两种方案，而 Memcached 没有持久化功能，数据全部存在内存之中
- Redis 原生支持集群模式，Memcached 没有原生的集群模式，需要依靠客户端来实现往集群中分片写入数据
- Redis 支持发布订阅模型、Lua 脚本、事务等功能，而 Memcached 不支持

****

#### Redis 和 Tair 对比

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

## 数据类型&应用场景

****

### Redis 的 key 设计规范

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

### String 类型

****

#### 基础概念

****

String 的底层结构是，简单动态字符串（Simple Dynamic String,SDS），特点：

- SDS 不仅可以保存文本数据，还可以保存二进制数据
- SDS 获取字符串长度的时间复杂度是 O(1)
- Redis 的 SDS API 是安全的，拼接字符串不会造成缓冲区溢出

在保存数字、小字符串时因为采用 INT 和 EMBSTR 编码，内存结构紧凑，只需要申请一次内存分配，效率更高，更节省内存。

对于超过44字节的大字符串时则需要采用 RAW 编码，申请额外的 SDS 空间，需要两次内存分配，效率较低，内存占用也较高，但大小不超过 512 MB，因此建议单个 value 尽量不要超过 44 字节。

****

#### 扩展操作

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

#### 应用场景

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

### Hash 类型

****

#### 基础概念

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

#### 扩展操作

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

#### 应用场景

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

### List 类型

****

#### 基础概念

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

#### 扩展操作

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

#### 应用场景

****

微信公众号发布文章或视频平台关注的博主发动态，在关注列表里面，这些消息要求按照时间进行推送

**解决方案**：

- 将订阅号消息放入用户关注列表 List 中
- 对于消息按照 `LPUSH` 或 `RPUSH` 的方式压入队列中
- 如，订阅号发布消息：`LPUSH msg:{userId} xxx`
- 查看最新消息：`LRANGE msg:{userId} 0 4`

****









