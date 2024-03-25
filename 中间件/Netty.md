# Java IO 模型

****

## 基础概念

****

在 I/O 操作中有这么两组概念，其中同步/异步 要和线程中的同步线程/异步线程要区分开，这里指的是同步IO / 异步IO

**阻塞/非阻塞**：

- 没有数据传过来时，读会阻塞直到有数据；缓冲区满时，写操作也会阻塞
- 非阻塞遇到这些情况，都是直接返回

**同步/异步**：

- 数据就绪后需要自己去读是同步
- 数据就绪后系统直接读好再回调给程序是异步

**常见的 IO 模型**：

- 同步阻塞 IO
- 同步非阻塞 IO
- IO 多路复用
- 信号IO
- 异步 IO

****

## Java BIO

****

BIO 是 blocking I/O 的简称，它是同步阻塞型 IO，其相关的类和接口在 java.io 下，简单来讲：

- BIO模型下的服务端为每一个请求都分配一个线程进行处理
- I/O 操作都是基于流 Stream 的操作

![image-20240324093936695](https://image.itbaima.cn/images/40/image-20240324096780993.png)

编写一个简单的 BioServer：

```java
public class BioServer {
    public static void main (String[] args) throws IOException {
        // BIO 模型的服务端要为每一个客户端建立一个对应的连接
        ServerSocket serverSocket = new ServerSocket(1145);
        while (true) {
            // 持续接受客户端的连接
            Socket accept = serverSocket.accept();
            // 为每一个客户端连接新开一个线程，执行对应的业务
            new Thread(new ClientService(accept)).start();
        }
    }

    static class ClientService implements Runnable {
        private Socket socket;
        
        public ClientService (Socket socket) {
            this.socket = socket;
        }

        @Override
        public void run() {
            System.out.println("执行对应的业务操作：" + socket);
        }
    }
}
```

对应来一个简单的 Client：

```java
public class Client {
    public static void main(String[] args) throws IOException {
        Socket socket = new Socket("127.0.0.1", 1145);
        System.out.println("建立连接：" + socket);
    }
}
```

这种 IO 模型的弊端十分明显：

- 线程开销：客户端的并发数与后端的线程数成1：1的比例，线程的创建、销毁是非常消耗系统资源的，随着并发量增大，服务端性能将显著下降，甚至会发生线程堆栈溢出等错误
- 线程阻塞：当连接创建后，如果该线程没有操作时，会进行阻塞操作，这样极大的浪费了服务器资源

****

## Java NIO

****

NIO，称之为 New IO 或是 non-block IO（非阻塞IO），这两种说法都可以，其实称之为非阻塞 IO 更恰当一些

NIO的三大核心组件：

- Buffer（缓冲区)
- Channel（通道）
- Selector（选择器/多路复用器）

****

### Buffer

****

- Buffer是一个对象，包含一些要写入或者读出的数据
- 原有的 IO 数据读写都是在 Stream 中，而 NIO 则是用 Buffer 预处理
- 读数据从缓冲区读，写数据也写入到缓冲区
- 缓冲区的本质是一个数组，底层支持多种实现（通常是字节数组实现），还提供了对数据结构化访问以及维护读写位置等操作

查看一下 java.nio 包下的 Buffer.java 源码中的几个私有属性：

```java
// Invariants: mark <= position <= limit <= capacity
    private int mark = -1;
    private int position = 0;
    private int limit;
    private int capacity;
```

mark <= position <= limit <= capacity 这个大小关系是在写模式下的：

- mark 就是一个标志位，capacity 是总容量
- position 是写入起始位置，limit 限制了可操作的最大地址

当 Buffer 需要读数据时会进行读写模式切换：

```java
public Buffer flip() {
        limit = position;
        position = 0;
        mark = -1;
        return this;
    }
```

- 这里将 limit 值更新为 position 的位置，即可读的区间不会超过已写入的区间
- 然后将 position 置 0，即读区间的起始位置

****

### Channel

****

Channe l是一个通道，管道，网络数据通过 Channel 读取和写入

Channel 和流 Stream 的不同之处：

![image-20240324104117449](https://image.itbaima.cn/images/40/image-20240324109182233.png)

-  Channel 是双向的
- 流只在一个方向上移动(InputStream/OutputStream)
- 而 Channel 可以用于读写同时进行，即 Channel 是全双工模式

Java 提供两个网络读写相关的 Channel：

- ServerSocketChannel：用于服务端和客户端建立连接，服务端必备，客户端不需要
- SocketChannel：用于客户端和服务端双向通信，服务端建立连接后需要创建该对象和客户端进行通信

![image-20240324104800899](https://image.itbaima.cn/images/40/image-20240324102738323.png)

这里 SocketChannel 在不同端上所支持的事件是不一样的：

| 端类型    | Channel 类型        | OP_ACCEPT | OP_CONNECT | OP_WRITE | OP_READ |
| --------- | ------------------- | --------- | ---------- | -------- | ------- |
| Client 端 | SocketChannel       |           | 支持       | 支持     | 支持    |
| Server 端 | ServerSocketChannel | 支持      |            |          |         |
| Server 端 | SocketChannel       |           |            | 支持     | 支持    |

****

### Selector

****

Selector（选择器/多路复用器）：

- Selector 会不断轮询注册在其上的 Channel
- 如果某个Channel 上面发生读或者写事件，即该Channel处于就绪状态，它就会被 Selector 轮询出来
- 被轮询出的 Channel 通过 selectedKeys 即可获取就绪的该 Channel 的集合，进行后续的I/O操作

![image-20240324110212214](https://image.itbaima.cn/images/40/image-20240324115893756.png)

基于 NIO 来实现一个服务端：

```java
public class NioServer {
    public static void main(String[] args) {
        try {
            //1、打开ServerSocketChannel,用于监听客户端的连接，它是所有客户端连接的父管道(代表客户端连接的管道都是通过它创建的)
            ServerSocketChannel serverSocketChannel = ServerSocketChannel.open();
            //2、绑定监听端口，设置连接为非阻塞模式
            serverSocketChannel.socket().bind(new InetSocketAddress(1145));
            serverSocketChannel.configureBlocking(false);
            //3、创建多路复用器Selector
            Selector selector = Selector.open();
            //4、将ServlerSocketChannel注册到selector上，监听客户端连接事件ACCEPT
            serverSocketChannel.register(selector, SelectionKey.OP_ACCEPT);
            //5、创建 Reactor线程，让多路复用器在 Reactor 线程中执行多路复用程序
            new Thread(new SingleReactor(selector)).start();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}

class SingleReactor implements  Runnable{

    private final Selector selector;
    public SingleReactor(Selector selector) {
        this.selector = selector;
    }

    public void run() {
        //6、selector轮询准备就绪的事件
        while (true) {
            try {
                selector.select(1000);
                Set<SelectionKey> selectionKeys = selector.selectedKeys();
                Iterator<SelectionKey> iterator = selectionKeys.iterator();
                while (iterator.hasNext()) {
                    SelectionKey selectionKey = iterator.next();
                    iterator.remove();
                    try {
                        processKey(selectionKey);
                    } catch (IOException e) {
                        e.printStackTrace();
                        if (selectionKey !=null ) {
                            selectionKey.cancel();
                            SelectableChannel channel = selectionKey.channel();
                            if (channel !=null) {
                                channel.close();
                            }
                        }
                    }
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void processKey(SelectionKey key) throws IOException {
        if (key.isValid()) {
            //7、根据准备就绪的事件类型分别处理
            if (key.isAcceptable()) {//客户端请求连接事件就绪
                //7.1、接收一个新的客户端连接，创建对应的SocketChannel,
                ServerSocketChannel serverSocketChannel = (ServerSocketChannel) key.channel();
                SocketChannel socketChannel = serverSocketChannel.accept();
                //7.2、设置socketChannel的非阻塞模式，并将其注册到Selector上，监听读事件
                socketChannel.configureBlocking(false);
                socketChannel.register(this.selector,SelectionKey.OP_READ);
            }
            if (key.isReadable()) {//读事件准备继续
                //7.1、读客户端发送过来的数据
                SocketChannel socketChannel = (SocketChannel) key.channel();
                ByteBuffer readBufer = ByteBuffer.allocate(1024);
                int readBytes = socketChannel.read(readBufer);
                //前面设置过socketChannel是非阻塞的，故要通过返回值判断读取到的字节数
                if (readBytes > 0) {
                    readBufer.flip();//读写模式切换
                    byte[] bytes = new byte[readBufer.remaining()];
                    readBufer.get(bytes);
                    String msg = new String(bytes,"utf-8");
                    //进行业务处理
                    String response = doService(msg);
                    //给客户端响应数据
                    System.out.println("服务端开始向客户端响应数据");
                    byte[] responseBytes = response.getBytes();
                    ByteBuffer writeBuffer = ByteBuffer.allocate(responseBytes.length);
                    writeBuffer.put(responseBytes);
                    writeBuffer.flip();
                    socketChannel.write(writeBuffer);
                }else if (readBytes < 0) {
                    //值为-1表示链路通道已经关闭
                    key.cancel();
                    socketChannel.close();
                }else {
                    //没读取到数据，忽略
                }
            }
        }
    }

    private String doService(String msg) {
        System.out.println("成功接收来自客户端发送过来的数据:"+msg);
        return "hello client,i am server!";
    }

}
```

对应的客户端实现：

```java
public class NioClient {

    public static void main(String[] args) {
        try {
            //1、窗口客户端SocketChannel,绑定客户端本地地址(不选默认随机分配一个可用地址)
            SocketChannel socketChannel = SocketChannel.open();
            //2、设置非阻塞模式,
            socketChannel.configureBlocking(false);
            //3、创建Selector
            Selector selector = Selector.open();
            //3、创建Reactor线程
            new Thread(new SingleReactorClient(socketChannel,selector)).start();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}

class SingleReactorClient implements  Runnable{
    private final SocketChannel socketChannel;
    private final Selector selector;

    public SingleReactorClient(SocketChannel socketChannel, Selector selector) {
        this.socketChannel = socketChannel;
        this.selector = selector;
    }

    public void run() {
        try {
            //连接服务端
            doConnect(socketChannel,selector);
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }

        //5、多路复用器执行多路复用程序
        while (true) {
            try {
                selector.select(1000);
                Set<SelectionKey> selectionKeys = selector.selectedKeys();
                Iterator<SelectionKey> iterator = selectionKeys.iterator();
                while (iterator.hasNext()) {
                    SelectionKey selectionKey = iterator.next();
                    processKey(selectionKey);
                    iterator.remove();
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void doConnect(SocketChannel sc, Selector selector) throws IOException {
        System.out.println("客户端成功启动,开始连接服务端");
        //3、连接服务端
        boolean connect = sc.connect(new InetSocketAddress("127.0.0.1", 1145));
        //4、将socketChannel注册到selector并判断是否连接成功，连接成功监听读事件，没有继续监听连接事件
        System.out.println("connect="+connect);
        if (connect) {
            sc.register(selector, SelectionKey.OP_READ);
            System.out.println("客户端成功连上服务端,准备发送数据");
            //开始进行业务处理，向服务端发送数据
            doService(sc);
        }else {
            sc.register(selector,SelectionKey.OP_CONNECT);
        }
    }

    private void processKey(SelectionKey key) throws IOException {
        if (key.isValid()) {
            //6、根据准备就绪的事件类型分别处理
            if (key.isConnectable()) {//服务端可连接事件准备就绪
                SocketChannel sc = (SocketChannel) key.channel();
                if (sc.finishConnect()) {
                    //6.1、向selector注册可读事件(接收来自服务端的数据)
                    sc.register(selector,SelectionKey.OP_READ);
                    //6.2、处理业务 向服务端发送数据
                    doService(sc);
                }else {
                    //连接失败，退出
                    System.exit(1);
                }
            }

            if (key.isReadable()) {//读事件准备继续
                //6.1、读服务端返回的数据
                SocketChannel sc = (SocketChannel) key.channel();
                ByteBuffer readBufer = ByteBuffer.allocate(1024);
                int readBytes = sc.read(readBufer);
                //前面设置过socketChannel是非阻塞的，故要通过返回值判断读取到的字节数
                if (readBytes > 0) {
                    readBufer.flip();//读写模式切换
                    byte[] bytes = new byte[readBufer.remaining()];
                    readBufer.get(bytes);
                    String msg = new String(bytes,"utf-8");
                    //接收到服务端返回的数据后进行相关操作
                    doService(msg);
                }else if (readBytes < 0) {
                    //值为-1表示链路通道已经关闭
                    key.cancel();
                    sc.close();
                }else {
                    //没读取到数据，忽略
                }
            }
        }
    }
    private static void doService(SocketChannel socketChannel) throws IOException {
        System.out.println("客户端开始向服务端发送数据:");
        //向服务端发送数据
        byte[] bytes = "hello nioServer,i am nioClient !".getBytes();
        ByteBuffer writeBuffer = ByteBuffer.allocate(bytes.length);
        writeBuffer.put(bytes);
        writeBuffer.flip();
        socketChannel.write(writeBuffer);
    }

    private String doService(String msg) {
        System.out.println("成功接收来自服务端响应的数据:"+msg);
        return "";
    }
}
```

****

## AIO

****

在NIO中，Selector 多路复用器在做轮询时，如果没有事件发生，也会进行阻塞，如何优化？

这里提出 AIO，它是 Asynchronous l/O 的简称（异步非阻塞 IO），是异步IO，该异步 IO 是需要依赖于操作系统底层的异步 IO 实现

![image-20240325093142421](https://image.itbaima.cn/images/40/image-20240325098792701.png)

- 用户线程通过系统调用，告知 kernel 内核启动某个 IO 操作，用户线程返回
- kernel 内核在整个 IO 操作（包括数据准备、数据复制)完成后，通知用户程序，用户执行后续的业务操作

目前该技术在 Windows 下实现成熟，但很少作为百万级以上或者说高并发应用的服务器操作系统来使用

Liux系统下，异步 IO 模型在 2.6 版本才引入，目前并不完善。所以 Liux 下，实现高并发网络编程时都是以 NIO 多路复用模型模式为主

****

# Reactor 线程模型

****

## 基础概念

****

Reactor 线程模型不是 Java专属，也不是 Netty 专属，它其实是一种并发编程模型，是一种思想，具有指导意义。

Reactor 模型中定义了三种角色：

- Reactor：负责监听和分配事件，将 I/O 事件分派给对应的 Handle，新的事件包含连接建立就绪、读就绪写就绪等
- Acceptor：处理客户端新连接，并分派请求到处理器链中
- Handler：将自身与事件绑定，执行非阻塞读/写任务，完成 Channel 的读入，完成处理业务逻辑后，负责将结果写出 Channel

****

## 单 Reactor

****

我们之前在 Java NIO 中实现的代码其实就是一个类似的 Reactor 单线程模型：

![image-20240324173722934](https://image.itbaima.cn/images/40/image-20240324171733664.png)

在 Reactor 单线程模型中：

- 一个单独的线程运行一个事件循环，负责监听事件的发生（如网络请求）并将对应的处理工作委托给相应的处理器
- 一旦事件被 Reactor检测到，就通知到程序中相应的事件处理器（Handler）来相应地处理这些事件

这样的模型好处是编码简单，实现容易，但是所有的业务都需要依赖单线程执行，很容易达到性能瓶颈，因此可以将业务抽离出来放到线程池中执行，这就是单 Reactor 多线程模型：

![image-20240324175554772](https://image.itbaima.cn/images/40/image-20240324173263805.png)

****

## 主从 Reactor

****

对于单 Reactor 多线程模型中，虽然我们已经将业务进行了分离，但是仍然存在缺陷：

- 假如有多个 Handler 在执行 read 操作，则当前的线程仍然被阻塞
- 对于其他 Client 发起的连接请求将会阻塞，这就存在丢失连接的风险

对于服务器来说，接收客户端的连接是比较重要的，因此将这部分操作单独用线程去操作：

![image-20240324181304451](https://image.itbaima.cn/images/40/image-20240324188957887.png)这里的 subReactor 可以有多个，但都只负责对连接建立事件的监听，已建立连接的 SocketChannel 将会注册到 MainReactor 中。

****

# Netty 概述

****

Netty 是由 JBOSS 提供的一个 java 开源框架，现为 Github上的独立项目，[项目地址](https://github.com/netty/netty)。

Netty 提供非阻塞的、事件驱动的网络应用程序框架和工具，用以快速开发高性能、高可靠性的网络服务器和客户端程序：

- 本质：网络应用程序框架
- 实现：异步、事件驱动
- 特性：高性能、可维护、快速开发
- 用途：开发服务器和客户端

****

## Netty 架构设计

****

![image-20240325151500031](https://image.itbaima.cn/images/40/image-20240325158390948.png)

核心：

- 可扩展的事件模型
- 统一的通信api，简化了通信编码
- 零拷贝机制与丰富的字节缓冲区

传输服务：

- 支持 socket 以及 datagram（数据报）
- http传输服务
- In-VM Pipe（管道协议，是jvm的一种进程)

协议支持：

- http 以及 websocket
- SSL安全套接字协议支持
- Google Protobuf（序列化框架)
- 支持 zlib、gzip 压缩，支持大文件的传输
- RTSP（实时流传输协议，是TCP/IP协议体系中的一个应用层协议)
- 支持二进制协议并且提供了完整的单元测试

****

## Netty 核心优势

****

**API隔离**：

- JDK 中 NIO 的一些 API 功能薄弱且复杂
- Netty 隔离了 JDK 中 NIO 的实现变化及实现细节
- 譬如：ByteBuffer -> ByteBuf 主要负责从底层的 IO 中读取数据到 ByteBuf
- 然后传递给应用程序，应用程序处理完之后封装为 Byte Buf，写回给 IO

**简化开发**：

- 使用 JDK 原生 API 需要对多线程要很熟悉
- 因为 NIO 涉及到 Reactor 设计模式，得对里面的原理要相当的熟悉

**高可用机制**：

- JDK 原生方式要实现高可用，需要自己实现断路重连、半包读写、粘包处理、失败缓存处理等相关操作
- 而 Netty 则做的更多，它解决了传输的一些问题譬如粘包半包现象，它支持常用的应用层协议，完善的断路重连等异常处理

**缺陷处理**

- JDK 的 NIO 存在 bug，如经典的 epoll bug，会导致 CPU100%
- 而 Netty 封装的更完善

****

## Netty 线程模型

****

![image-20240325210837433](https://image.itbaima.cn/images/40/image-20240325215461744.png)

Netty 线程模型是基于 Reactor 模型实现的，对 Reactor 的三种模式都有非常好的支持，并做了一定的改进，也非常的灵活，一般情况，在服务端会采用主从架构模型。

对于主从 Reactor 架构：

![image-20240325211729921](https://image.itbaima.cn/images/40/image-20240325212635047.png)



Netty 抽象出两组线程池：

- BossGroup 和 WorkerGroup，每个线程池中都有 EventLoop 线程（可以是OIO,NIO,AIO)
- BossGroup 中的线程专门负责和客户端建立连接
- WorkerGroup 中的线程专门负责处理连接上的读写
- EventLoopGroup 相当于一个事件循环组，这个组中含有多个事件循环

EventLoop 表示一个不断循环的执行事件处理的线程，每个 EventLoop 都包含一个 Selector，用于监听注册在其上的 Socket 网络连接(Channel)

每个 Boss EventLoop 中循环执行以下三个步骤：

- select：轮训注册在其上的 ServerSocketChannel 的 accept 事件（OP_ACCEPT事件)
- processSelectedKeys：处理 accept 事件，与客户端建立连接，生成一个 SocketChannel，并将其注册到某个WorkerEventLoop上的 Selector 上
- runAllTasks：再去以此循环处理任务队列中的其他任务

每个 WorkerEventLoop 中循环执行以下三个步骤：

- select：轮训注册在其上的 SocketChannel 的 read/write 事件（OP READ/OP_WRITE事件)
- processSelectedKeys：在对应的 SocketChannel上处理 read/write 事件
- runAllTasks：再去以此循环处理任务队列中的其他任务

在以上两个 processSelectedKeys 步骤中，会使用 Pipeline(管道)，Pipeline中引用了 Channel，即通过 Pipeline 可以获取到对
应的Channel，Pipeline 中维护了很多的处理器（拦截处理器、过滤处理器、自定义处理器等）

****

## Pipeline 和 Handler

****

### ChannelPipeline 处理流程

****

ChannelPipeline 提供了 ChannelHandler 链的容器：

![image-20240325213317524](https://image.itbaima.cn/images/40/image-20240325215557848.png)

以服务端程序为例：

- 客户端发送过来的数据要接收，读取处理，我们称数据是入站的
- 入站的数据交由各个 Handler 处理，即执行具体的业务逻辑
- 如果服务器想向客户端写回数据，也需要经过一系列 Handler 处理，我们称数据是出站的

Handler 的头节点和尾节点都是初始化好的，用户无需自己实现，只需要实现中间的 Handler 即可

当一个事件如接收到数据或者异常发生时，这个事件会按照 ChannelPipeline 中的 ChannelHandler 的顺序被处理，每个ChannelHandler 可以传递给下一个，直到有一个处理器处理它或者 Pipeline 中没有更多的处理器了，这个处理过程是**责任链设计模式**的体现。

****

###  ChannelHandler 体系结构

****

在 ChannelPipeline 的处理流程中，对于入站和出站的数据，对应的 ChannelHandler 的类型不同：

- ChannellnboundHandler：入站事件处理器
- ChannelOutBoundHandler：出站事件处理器
- ChannelHandlerAdapter：提供了一些方法的默认实现，可减少用户对于ChannelHandler的编写
- ChannelDuplexHandler：混合型，既能处理入站事件又能处理出站事件

![image-20240325214658941](https://image.itbaima.cn/images/40/image-20240325214690468.png)

inbound 入站事件处理顺序（方向）是由链表的头到链表尾，outbound 事件的处理顺序是由链表尾到链表头：

- inbound 入站事件由 Netty 内部触发，最终由 Netty 外部的代码消费
- outbound 事件由 Netty 外部的代码触发，最终由 Netty 内部消费

****



