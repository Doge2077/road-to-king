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

