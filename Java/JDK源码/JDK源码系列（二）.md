# ArrayList 类

****

## ArrayList 类结构

****

ArrayList 是一个用数组实现的集合，支持随机访问，元素有序且可以重复：

- `ArrayList` 是一种变长的集合类，基于定长数组实现
- `ArrayList` 允许空值和重复元素，当往 ArrayList 中添加的元素数量大于其底层数组容量时，其会通过**扩容**机制重新生成一个更大的数组
- `ArrayList` 底层基于数组实现，所以其可以保证在 `O(1)` 复杂度下完成随机查找操作
- `ArrayList` 是非线程安全类，并发环境下，多个线程同时操作 ArrayList，会引发不可预知的异常或错误。

```java
public class ArrayList<E> extends AbstractList<E>
        implements List<E>, RandomAccess, Cloneable, java.io.Serializable
```

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220214151452756.png)

- 实现 RandomAccess 接口：
  - 这是一个标记接口，一般此标记接口用于 `List`实现，以表明它们支持快速（通常是恒定时间）的随机访问
- 实现 Cloneable 接口：
  - Cloneable 和 RandomAccess 接口一样也是一个标记接口，接口内无任何方法体和常量的声明
  - 如果想克隆对象，必须要  实现 Cloneable 接口，表明该类是可以被克隆的

- 实现 Serializable 接口：
  - 标记接口，表示能被序列化

- 实现 List 接口：
  - 这个接口是 List 类集合的上层接口，定义了实现该接口的类都必须要实现的一组方法

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220214152521279.png)

****

## 字段属性

****

```java
//集合的默认大小
private static final int DEFAULT_CAPACITY = 10;

//空的数组实例
private static final Object[] EMPTY_ELEMENTDATA = {};

//这也是一个空的数组实例，和EMPTY_ELEMENTDATA空数组相比是用于了解添加元素时数组膨胀多少
private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = {};

//存储 ArrayList集合的元素，集合的长度即这个数组的长度
//1、当 elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA 时将会清空 ArrayList
//2、当添加第一个元素时，elementData 长度会扩展为 DEFAULT_CAPACITY=10
transient Object[] elementData;

//表示集合的长度
private int size;
```

****

## 类构造器

****

### 无参构造

```java
public ArrayList() {
	this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
}
```

此无参构造函数将创建一个 DEFAULTCAPACITY_EMPTY_ELEMENTDATA 声明的数组，注意此时初始容量是0，而不是大家以为的 10。

**注意**：根据默认构造函数创建的集合，`ArrayList list = new ArrayList();` 此时集合长度是 0

****

### 重载：有参构造 ArrayList(int initialCapacity)

```java
public ArrayList(int initialCapacity) {
    if (initialCapacity > 0) {
        this.elementData = new Object[initialCapacity];
    } else if (initialCapacity == 0) {
        this.elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new IllegalArgumentException("Illegal Capacity: "+
                                           initialCapacity);
    }
}
```

初始化集合大小创建 ArrayList 集合。当大于0时，给定多少那就创建多大的数组

当等于0时，创建一个空数组；当小于0时，抛出异常

****

### 重载：ArrayList(Collection<? extends E> c)

```java
public ArrayList(Collection<? extends E> c) {
    elementData = c.toArray();
    if ((size = elementData.length) != 0) {
        // c.toArray might (incorrectly) not return Object[] (see 6260652)
        if (elementData.getClass() != Object[].class)
            elementData = Arrays.copyOf(elementData, size, Object[].class);
    } else {
        // replace with empty array.
        this.elementData = EMPTY_ELEMENTDATA;
    }
}
```

将已有的集合复制到 ArrayList 集合中

****

## 添加元素

****

源码：

```java
public boolean add(E e) {
	ensureCapacityInternal(size + 1);  //添加元素之前，首先要确定集合的大小(是否需要扩容)
	elementData[size++] = e;
	return true;
}
```

如上所示，在通过调用 add 方法添加元素之前，我们要首先调用 ensureCapacityInternal 方法来确定集合的大小，如果集合满了，则要进行扩容操作：

```java
private void ensureCapacityInternal(int minCapacity) {//这里的minCapacity 是集合当前大小+1
    //elementData 是实际用来存储元素的数组，注意数组的大小和集合的大小不是相等的，前面的size是指集合大小
    ensureExplicitCapacity(calculateCapacity(elementData, minCapacity));
}

private static int calculateCapacity(Object[] elementData, int minCapacity) {
    if (elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {//如果数组为空，则从size+1的值和默认值10中取最大的
        return Math.max(DEFAULT_CAPACITY, minCapacity);
    }
    return minCapacity;//不为空，则返回size+1
}

private void ensureExplicitCapacity(int minCapacity) {
    modCount++;

    // overflow-conscious code
    if (minCapacity - elementData.length > 0)
        grow(minCapacity);
}
```

在 ensureExplicitCapacity 方法中，首先对修改次数 modCount 加一

这里的 modCount 给 ArrayList 的迭代器使用的，在并发操作被修改时，提供快速失败行为（保证modCount在迭代期间不变，否则抛出ConcurrentModificationException异常，可以查看源码865行），接着判断minCapacity是否大于当前ArrayList内部数组长度，大于的话调用grow方法对内部数组elementData扩容，grow方法代码如下：

```java
private void grow(int minCapacity) {
    int oldCapacity = elementData.length;//得到原始数组的长度
    int newCapacity = oldCapacity + (oldCapacity >> 1);//新数组的长度等于原数组长度的1.5倍
    if (newCapacity - minCapacity < 0)//当新数组长度仍然比minCapacity小，则为保证最小长度，新数组等于minCapacity
        newCapacity = minCapacity;
    //MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8 = 2147483639
    if (newCapacity - MAX_ARRAY_SIZE > 0)//当得到的新数组长度比 MAX_ARRAY_SIZE 大时，调用 hugeCapacity 处理大数组
        newCapacity = hugeCapacity(minCapacity);
    //调用 Arrays.copyOf 将原数组拷贝到一个大小为newCapacity的新数组（注意是拷贝引用）
    elementData = Arrays.copyOf(elementData, newCapacity);
}

private static int hugeCapacity(int minCapacity) {
    if (minCapacity < 0) //
        throw new OutOfMemoryError();
    return (minCapacity > MAX_ARRAY_SIZE) ? //minCapacity > MAX_ARRAY_SIZE,则新数组大小为Integer.MAX_VALUE
        Integer.MAX_VALUE :
    MAX_ARRAY_SIZE;
}
```

扩容的核心方法就是调用前面我们讲过的**Arrays.copyOf** 方法，创建一个更大的数组，然后将原数组元素拷贝过去即可

对于 ArrayList 集合添加元素，总结一下：

- 当通过 ArrayList() 构造一个空集合，初始长度是为0的，第 1 次添加元素，会创建一个长度为10的数组，并将该元素赋值到数组的第一个位置。
- 第 2 次添加元素，集合不为空，而且由于集合的长度size+1是小于数组的长度10，所以直接添加元素到数组的第二个位置，不用扩容。
- 第 11 次添加元素，此时 size+1 = 11，而数组长度是10，这时候创建一个长度为10+10\*0.5 = 15 的数组（扩容1.5倍），然后将原数组元素引用拷贝到新数组。并将第 11 次添加的元素赋值到新数组下标为10的位置。
- 第 Integer.MAX_VALUE - 8 = 2147483639，然后 2147483639%1.5=1431655759（这个数是要进行扩容） 次
- 添加元素，为了防止溢出，此时会直接创建一个 1431655759+1 大小的数组，这样一直，每次添加一个元素，都只扩大一个范围。第 Integer.MAX_VALUE - 7 次添加元素时，创建一个大小为 Integer.MAX_VALUE 的数组，在进行元素添加。
- 第 Integer.MAX_VALUE + 1 次添加元素时，抛出 OutOfMemoryError 异常。

**注意：可以向集合中添加 null ，因为数组可以有 null 值存在**：

```java
Object[] obj = {null,1};

ArrayList list = new ArrayList();
list.add(null);
list.add(1);
System.out.println(list.size());//2
```

****

## 删除元素

****

```java
public E remove(int index) {
    rangeCheck(index);  //判断给定索引的范围，超过集合大小则抛出异常

    modCount++;
    E oldValue = elementData(index);  //得到索引处的删除元素

    int numMoved = size - index - 1;
    if (numMoved > 0)  //size-index-1 > 0 表示 0<= index < (size-1),即索引不是最后一个元素
        //通过 System.arraycopy()将数组elementData 的下标index+1之后长度为 numMoved 的元素拷贝到从index开始的位置
        System.arraycopy(elementData, index+1, elementData, index,
                         numMoved);
    elementData[--size] = null; //更新 size 的同时将数组最后一个元素置为 null，便于垃圾回收

    return oldValue;
}
```

remove(int index) 方法表示删除索引index处的元素

首先通过 rangeCheck(index) 方法判断给定索引的范围，超过集合大小则抛出异常

接着通过 System.arraycopy 方法对数组进行自身拷贝

```java
/*
*　src:源数组
　　srcPos:源数组要复制的起始位置
　　dest:目的数组
　　destPos:目的数组放置的起始位置
　　length:复制的长度
　　注意：src 和 dest都必须是同类型或者可以进行转换类型的数组。
*/
public static native void arraycopy(Object src,  int  srcPos,
                                        Object dest, int destPos,
                                        int length);
```

****

## 修改元素

****

通过调用 set(int index, E element) 方法在指定索引 index 处的元素替换为 element。并返回原数组的元素。

```java
public E set(int index, E element) {
    rangeCheck(index);//判断索引合法性

    E oldValue = elementData(index);//获得原数组指定索引的元素
    elementData[index] = element;//将指定所引处的元素替换为 element
    return oldValue;//返回原数组索引元素
}
```

通过调用 rangeCheck(index) 来检查索引合法性

```java
private void rangeCheck(int index) {
	if (index >= size)
		throw new IndexOutOfBoundsException(outOfBoundsMsg(index));
}
```

当索引为负数时，会抛出 java.lang.ArrayIndexOutOfBoundsException 异常。

当索引大于集合长度时，会抛出 IndexOutOfBoundsException 异常。

****

## 查找元素

****

```java
public E get(int index) {
	rangeCheck(index);

	return elementData(index);
}
```

同理，首先还是判断给定索引的合理性，然后直接返回处于该下标位置的数组元素。

****

## 遍历集合

****

### 普通 for 循环遍历

****

前面我们介绍查找元素时，知道可以通过get(int index)方法，根据索引查找元素，那么遍历同理：

```java
ArrayList list = new ArrayList();
list.add("a");
list.add("b");
list.add("c");
for(int i = 0 ; i < list.size() ; i ++){
    System.out.print(list.get(i) + " ");
}
```

****

### 迭代器 iterator

****

```java
ArrayList<String> list = new ArrayList<>();
list.add("a");
list.add("b");
list.add("c");
Iterator<String> it = list.iterator();
while(it.hasNext()){
    String str = it.next();
    System.out.print(str + " ");
}
```

在介绍 ArrayList 时，我们知道该类实现了 List 接口，而 List 接口又继承了 Collection 接口，Collection 接口又继承了 Iterable 接口，该接口有个 Iterator iterator() 方法，能获取 Iterator 对象，能用该对象进行集合遍历

ArrayList 类中的该方法实现：

```java
public Iterator<E> iterator() {
    return new Itr();
}
```

该方法是返回一个 Itr 对象，这个类是 ArrayList 的内部类。

```java
private class Itr implements Iterator<E> {
    int cursor;       //游标， 下一个要返回的元素的索引
    int lastRet = -1; // 返回最后一个元素的索引; 如果没有这样的话返回-1.
    int expectedModCount = modCount;

    //通过 cursor ！= size 判断是否还有下一个元素
    public boolean hasNext() {
        return cursor != size;
    }

    @SuppressWarnings("unchecked")
    public E next() {
        checkForComodification();//迭代器进行元素迭代时同时进行增加和删除操作，会抛出异常
        int i = cursor;
        if (i >= size)
            throw new NoSuchElementException();
        Object[] elementData = ArrayList.this.elementData;
        if (i >= elementData.length)
            throw new ConcurrentModificationException();
        cursor = i + 1;//游标向后移动一位
        return (E) elementData[lastRet = i];//返回索引为i处的元素，并将 lastRet赋值为i
    }

    public void remove() {
        if (lastRet < 0)
            throw new IllegalStateException();
        checkForComodification();

        try {
            ArrayList.this.remove(lastRet);//调用ArrayList的remove方法删除元素
            cursor = lastRet;//游标指向删除元素的位置，本来是lastRet+1的，这里删除一个元素，然后游标就不变了
            lastRet = -1;//lastRet恢复默认值-1
            expectedModCount = modCount;//expectedModCount值和modCount同步，因为进行add和remove操作，modCount会加1
        } catch (IndexOutOfBoundsException ex) {
            throw new ConcurrentModificationException();
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public void forEachRemaining(Consumer<? super E> consumer) {//便于进行forEach循环
        Objects.requireNonNull(consumer);
        final int size = ArrayList.this.size;
        int i = cursor;
        if (i >= size) {
            return;
        }
        final Object[] elementData = ArrayList.this.elementData;
        if (i >= elementData.length) {
            throw new ConcurrentModificationException();
        }
        while (i != size && modCount == expectedModCount) {
            consumer.accept((E) elementData[i++]);
        }
        // update once at end of iteration to reduce heap write traffic
        cursor = i;
        lastRet = i - 1;
        checkForComodification();
    }

    //前面在新增元素add() 和 删除元素 remove() 时，我们可以看到 modCount++。修改set() 是没有的
    //也就是说不能在迭代器进行元素迭代时进行增加和删除操作，否则抛出异常
    final void checkForComodification() {
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
    }
}
```

注意在进行 next() 方法调用的时候，会进行 checkForComodification() 调用，该方法表示迭代器进行元素迭代时，如果同时进行增加和删除操作，会抛出 ConcurrentModificationException 异常。

例如：

```java
ArrayList<String> list = new ArrayList<>();
list.add("a");
list.add("b");
list.add("c");
Iterator<String> it = list.iterator();
while(it.hasNext()){
    String str = it.next();
    System.out.print(str + " ");
    list.remove(str);//集合遍历时进行删除或者新增操作，都会抛出 ConcurrentModificationException 异常
    //list.add(str);
    list.set(0, str);//修改操作不会造成异常
}
```

解决办法是不调用 ArrayList.remove() 方法，转而调用迭代器的 remove() 方法：

```java
Iterator<String> it = list.iterator();
while(it.hasNext()){
    String str = it.next();
    System.out.print(str + " ");
    it.remove(); // 调用迭代器的 remove() 方法
}
```

**注意：迭代器只能向后遍历，不能向前遍历，能够删除元素，但是不能新增元素。**

****

### 迭代器的变种 forEach

****

```java
ArrayList<String> list = new ArrayList<>();
 list.add("a");
 list.add("b");
 list.add("c");
for(String str : list){
    System.out.print(str + " ");
}
```

这种语法可以看成是 JDK 的一种语法糖，通过反编译 class 文件，我们可以看到生成的 java 文件，其具体实现还是通过调用 Iterator 迭代器进行遍历的。如下：

```java
ArrayList list = new ArrayList();
        list.add("a");
        list.add("b");
        list.add("c");
        String str;
        for (Iterator iterator1 = list.iterator(); iterator1.hasNext(); System.out.print((new StringBuilder(String.valueOf(str))).append(" ").toString()))
            str = (String)iterator1.next();
```

总结：

- ArrayList可以存放null。
- ArrayList 本质上就是一个elementData数组。
- ArrayList 区别于数组的地方在于能够自动扩展大小，其中关键的方法就是gorw()方法。
- ArrayList 由于本质是数组，所以它在数据的查询方面会很快，而在插入删除这些方面，性能下降很多，底层要移动很多数据才能达到应的效果。

****

# LinkedList 类

****

## LinkedList 类结构图

****

```java
 public class LinkedList<E>
     extends AbstractSequentialList<E>
     implements List<E>, Deque<E>, Cloneable, java.io.Serializable
```

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220221114859670.png)

 

- 和 ArrayList 集合一样，LinkedList 集合也实现了Cloneable接口和Serializable接口，分别用来支持克隆以及支持序列化。
- List 接口也不用多说，定义了一套 List 集合类型的方法规范。

**注意**：相对于 ArrayList 集合，LinkedList 集合多实现了一个 `Deque` 接口，这是一个双向队列接口，双向队列就是两端都可以进行增加和删除操作。

****

## 字段属性

****

```java
//链表元素（节点）的个数
transient int size = 0;

/**
*指向第一个节点的指针
*/
transient Node<E> first;

/**
*指向最后一个节点的指针
*/
transient Node<E> last;
```

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220221134536731.png)

**注意**：这里出现了一个 Node 类，这是 LinkedList 类中的一个内部类，其中每一个元素就代表一个 Node 类对象，LinkedList 集合就是由许多个 Node 对象类似于手拉着手构成。

```java
private static class Node<E> {
    
    E item;//实际存储的元素
    Node<E> next;//指向上一个节点的引用
    Node<E> prev;//指向下一个节点的引用

    //构造函数
    Node(Node<E> prev, E element, Node<E> next) {
        this.item = element;
        this.next = next;
        this.prev = prev;
    }
}
```

****

## 类构造器

****

无参构造：

```java
public LinkedList() {
}
```

有参构造：

```java
public LinkedList(Collection<? extends E> c) {
    this();
    addAll(c);
}
```

LinkedList 有两个构造函数，第一个是默认的空的构造函数，第二个是将已有元素的集合Collection 的实例添加到 LinkedList 中，调用的是 addAll() 方法

**注意**：LinkedList 是没有初始化链表大小的构造函数，因为链表不像数组，一个定义好的数组是必须要有确定的大小，然后去分配内存空间，而链表不一样，它没有确定的大小，通过指针的移动来指向下一个内存地址的分配。

****

## 添加元素

****

### addFirst(E e)

****

将指定元素添加到链表头：

```java
//将指定的元素附加到链表头节点
public void addFirst(E e) {
    linkFirst(e);
}

private void linkFirst(E e) {
    final Node<E> f = first;  //将头节点赋值给 f
    final Node<E> newNode = new Node<>(null, e, f);  //将指定元素构造成一个新节点，此节点的指向下一个节点的引用为头节点
    first = newNode;     //将新节点设为头节点，那么原先的头节点 f 变为第二个节点
    if (f == null)       //如果第二个节点为空，也就是原先链表是空
        last = newNode;  //将这个新节点也设为尾节点（前面已经设为头节点了）
    else
        f.prev = newNode;//将原先的头节点的上一个节点指向新节点
    size++;  //节点数加1
    modCount++;  //和ArrayList中一样，iterator和listIterator方法返回的迭代器和列表迭代器实现使用。
}
```

****

###  addLast(E e)和add(E e)

****

将指定元素添加到链表尾：

```java
//将元素添加到链表末尾
public void addLast(E e) {
    linkLast(e);
}
//将元素添加到链表末尾
public boolean add(E e) {
    linkLast(e);
    return true;
}
void linkLast(E e) {
    final Node<E> l = last;  //将l设为尾节点
    final Node<E> newNode = new Node<>(l, e, null);  //构造一个新节点，节点上一个节点引用指向尾节点l
    last = newNode;       //将尾节点设为创建的新节点
    if (l == null)        //如果尾节点为空，表示原先链表为空
        first = newNode;  //将头节点设为新创建的节点（尾节点也是新创建的节点）
    else
        l.next = newNode; //将原来尾节点下一个节点的引用指向新节点
    size++;  //节点数加1
    modCount++;  //和ArrayList中一样，iterator和listIterator方法返回的迭代器和列表迭代器实现使用。
}
```

****

### add(int index, E element)

****

将指定的元素插入此列表中的指定位置：

```java
//将指定的元素插入此列表中的指定位置
public void add(int index, E element) {
    //判断索引 index >= 0 && index <= size中时抛出IndexOutOfBoundsException异常
    checkPositionIndex(index);

    if (index == size)//如果索引值等于链表大小
        linkLast(element);//将节点插入到尾节点
    else
        linkBefore(element, node(index));
}

void linkLast(E e) {
    final Node<E> l = last;//将l设为尾节点
    final Node<E> newNode = new Node<>(l, e, null);//构造一个新节点，节点上一个节点引用指向尾节点l
    last = newNode;//将尾节点设为创建的新节点
    if (l == null)//如果尾节点为空，表示原先链表为空
        first = newNode;//将头节点设为新创建的节点（尾节点也是新创建的节点）
    else
        l.next = newNode;//将原来尾节点下一个节点的引用指向新节点
    size++;//节点数加1
    modCount++;//和ArrayList中一样，iterator和listIterator方法返回的迭代器和列表迭代器实现使用。
}

Node<E> node(int index) {
    if (index < (size >> 1)) {//如果插入的索引在前半部分
        Node<E> x = first;//设x为头节点
        for (int i = 0; i < index; i++)//从开始节点到插入节点索引之间的所有节点向后移动一位
            x = x.next;
        return x;
    } else {//如果插入节点位置在后半部分
        Node<E> x = last;//将x设为最后一个节点
        for (int i = size - 1; i > index; i--)//从最后节点到插入节点的索引位置之间的所有节点向前移动一位
            x = x.prev;
        return x;
    }
}

void linkBefore(E e, Node<E> succ) {
    final Node<E> pred = succ.prev;//将pred设为插入节点的上一个节点
    final Node<E> newNode = new Node<>(pred, e, succ);//将新节点的上引用设为pred,下引用设为succ
    succ.prev = newNode;//succ的上一个节点的引用设为新节点
    if (pred == null)//如果插入节点的上一个节点引用为空
        first = newNode;//新节点就是头节点
    else
        pred.next = newNode;//插入节点的下一个节点引用设为新节点
    size++;
    modCount++;
}
```

****

### addAll(Collection<? extends E> c)

****

按照指定集合的迭代器返回的顺序，将指定集合中的所有元素追加到此列表的末尾

addAll有两个重载函数：

- addAll(Collection<? extends E>)型
- addAll(int, Collection<? extends E>)型

我们平时习惯调用的 `addAll(Collection<? extends E>)` 型会转化为 `addAll(int, Collection<? extends E>)` 型

addAll(c)：

```java
//按照指定集合的••迭代器返回的顺序，将指定集合中的所有元素追加到此列表的末尾。
public boolean addAll(Collection<? extends E> c) {
    return addAll(size, c);
}
//真正核心的地方就是这里了，记得我们传过来的是size，c
public boolean addAll(int index, Collection<? extends E> c) {
    //检查index这个是否为合理。这个很简单，自己点进去看下就明白了。
    checkPositionIndex(index);
    //将集合c转换为Object数组 a
    Object[] a = c.toArray();
    //数组a的长度numNew，也就是由多少个元素
    int numNew = a.length;
    if (numNew == 0)
        //集合c是个空的，直接返回false，什么也不做。
        return false;
    //集合c是非空的，定义两个节点(内部类)，每个节点都有三个属性，item、next、prev。
    Node<E> pred, succ;
    //构造方法中传过来的就是index==size
    if (index == size) {
        //linkedList中三个属性：size、first、last。 size：链表中的元素个数。 first：头节点  last：尾节点，就两种情况能进来这里

        //情况一、：构造方法创建的一个空的链表，那么size=0，last、和first都为null。linkedList中是空的。什么节点都没有。succ=null、pred=last=null

        //情况二、：链表中有节点，size就不是为0，first和last都分别指向第一个节点，和最后一个节点，在最后一个节点之后追加元素，就得记录一下最后一个节点是什么，所以把last保存到pred临时节点中。
        succ = null;
        pred = last;
    } else {
        //情况三、index！=size，说明不是前面两种情况，而是在链表中间插入元素，那么就得知道index上的节点是谁，保存到succ临时节点中，然后将succ的前一个节点保存到pred中，这样保存了这两个节点，就能够准确的插入节点了
        //举个简单的例子，有2个位置，1、2、如果想插数据到第二个位置，双向链表中，就需要知道第一个位置是谁，原位置也就是第二个位置上是谁，然后才能将自己插到第二个位置上。如果这里还不明白，先看一下开头对于各种链表的删除，add操作是怎么实现的。
        succ = node(index);
        pred = succ.prev;
    }
    //前面的准备工作做完了，将遍历数组a中的元素，封装为一个个节点。
    for (Object o : a) {
        @SuppressWarnings("unchecked") E e = (E) o;
        //pred就是之前所构建好的，可能为null、也可能不为null，为null的话就是属于情况一、不为null则可能是情况二、或者情况三
        Node<E> newNode = new Node<>(pred, e, null);
        //如果pred==null，说明是情况一，构造方法，是刚创建的一个空链表，此时的newNode就当作第一个节点，所以把newNode给first头节点
        if (pred == null)
            first = newNode;
        else
            //如果pred！=null，说明可能是情况2或者情况3，如果是情况2，pred就是last，那么在最后一个节点之后追加到newNode，如果是情况3，在中间插入，pred为原index节点之前的一个节点，将它的next指向插入的节点，也是对的
            pred.next = newNode;
        //然后将pred换成newNode，注意，这个不在else之中，请看清楚了。
        pred = newNode;
    }
    if (succ == null) {
        //如果succ==null，说明是情况一或者情况二，
        //情况一、构造方法，也就是刚创建的一个空链表，pred已经是newNode了，last=newNode，所以linkedList的first、last都指向第一个节点。
        //情况二、在最后节后之后追加节点，那么原先的last就应该指向现在的最后一个节点了，就是newNode。
        last = pred;
    } else {
        //如果succ！=null，说明可能是情况三、在中间插入节点，举例说明这几个参数的意义，有1、2两个节点，现在想在第二个位置插入节点newNode，根据前面的代码，pred=newNode，succ=2，并且1.next=newNode，1已经构建好了，pred.next=succ，相当于在newNode.next = 2； succ.prev = pred，相当于 2.prev = newNode， 这样一来，这种指向关系就完成了。first和last不用变，因为头节点和尾节点没变
        pred.next = succ;
        //。。
        succ.prev = pred;
    }
    //增加了几个元素，就把 size = size +numNew 就可以了
    size += numNew;
    modCount++;
    return true;
}
```

说明：参数中的index表示在索引下标为index的结点（实际上是第index + 1个结点）的前面插入。　　　　　

在addAll函数中，addAll函数中还会调用到node函数，get函数也会调用到node函数，此函数是根据索引下标找到该结点并返回，具体代码如下：

```java
Node<E> node(int index) {
    // 判断插入的位置在链表前半段或者是后半段
    if (index < (size >> 1)) { // 插入位置在前半段
        Node<E> x = first; 
        for (int i = 0; i < index; i++) // 从头结点开始正向遍历
            x = x.next;
        return x; // 返回该结点
    } else { // 插入位置在后半段
        Node<E> x = last; 
        for (int i = size - 1; i > index; i--) // 从尾结点开始反向遍历
            x = x.prev;
        return x; // 返回该结点
    }
}
```

说明：在根据索引查找结点时，会有一个小优化，结点在前半段则从头开始遍历，在后半段则从尾开始遍历，这样就保证了只需要遍历最多一半结点就可以找到指定索引的结点。

****

## 修改元素

****

通过调用 set(int index, E element) 方法，用指定的元素替换此列表中指定位置的元素

```java
public E set(int index, E element) {
    //判断索引 index >= 0 && index <= size中时抛出IndexOutOfBoundsException异常
    checkElementIndex(index);
    Node<E> x = node(index);//获取指定索引处的元素
    E oldVal = x.item;
    x.item = element;//将指定位置的元素替换成要修改的元素
    return oldVal;//返回指定索引位置原来的元素
}
```

这里主要是通过 node(index) 方法获取指定索引位置的节点，然后修改此节点位置的元素即可。

****

## 查找元素

****

### getFirst()

****

返回此列表中的第一个元素：

```java
public E getFirst() {
    final Node<E> f = first;  // 返回第一个节点即可
    if (f == null)
        throw new NoSuchElementException();
    return f.item;
}
```

****

### getLast()

****

返回此列表中的最后一个元素：

```java
public E getLast() {
    final Node<E> l = last;  // 返回尾节点
    if (l == null)
        throw new NoSuchElementException();
    return l.item;
}
```

****

### get(int index)

****

返回指定索引处的元素：

```java
public E get(int index) {
    checkElementIndex(index);
    return node(index).item;
}
```

 这里分为两部分查找：

```java
/**
* Returns the (non-null) Node at the specified element index.
*/
Node<E> node(int index) {
    // assert isElementIndex(index);
    //"<<":*2的几次方 “>>”:/2的几次方，例如：size<<1：size*2的1次方，
    //这个if中就是查询前半部分
    if (index < (size >> 1)) {//index<size/2
        Node<E> x = first;
        for (int i = 0; i < index; i++)
            x = x.next;
        return x;
    } else {//前半部分没找到，所以找后半部分
        Node<E> x = last;
        for (int i = size - 1; i > index; i--)
            x = x.prev;
        return x;
    }
}
```

 即查找的过程：

- 先从第头节点向后遍历到链表中部查找
- 再从尾部节点遍历向前遍历到中部查找

****

### indexOf(Object o)

****

返回此列表中指定元素第一次出现的索引，如果此列表不包含元素，则返回-1

```java
//返回此列表中指定元素第一次出现的索引，如果此列表不包含元素，则返回-1。
public int indexOf(Object o) {
    int index = 0;
    if (o == null) {  //如果查找的元素为null(LinkedList可以允许null值)
        for (Node<E> x = first; x != null; x = x.next) {  //从头结点开始不断向下一个节点进行遍历
            if (x.item == null)
                return index;
            index++;
        }
    } else {  //如果查找的元素不为null
        for (Node<E> x = first; x != null; x = x.next) {
            if (o.equals(x.item))
                return index;
            index++;
        }
    }
    return -1;  //找不到返回-1
}
```

****

## 删除元素

****

### remove()和removeFirst()

****

从此列表中移除并返回第一个元素：

```java
//从此列表中移除并返回第一个元素
public E remove() {
    return removeFirst();
}

//从此列表中移除并返回第一个元素
public E removeFirst() {
    final Node<E> f = first;//f设为头结点
    if (f == null)
        throw new NoSuchElementException();//如果头结点为空，则抛出异常
    return unlinkFirst(f);
}

private E unlinkFirst(Node<E> f) {
    // assert f == first && f != null;
    final E element = f.item;
    final Node<E> next = f.next;  //next 为头结点的下一个节点
    f.item = null;
    f.next = null;     // 将节点的元素以及引用都设为 null，便于垃圾回收
    first = next;      //修改头结点为第二个节点
    if (next == null)  //如果第二个节点为空（当前链表只存在第一个元素）
        last = null;   //那么尾节点也置为 null
    else
        next.prev = null;  //如果第二个节点不为空，那么将第二个节点的上一个引用置为 null
    size--;
    modCount++;
    return element;
}
```

****

### removeLast()

****

从该列表中删除并返回最后一个元素：

```java
//从该列表中删除并返回最后一个元素
public E removeLast() {
    final Node<E> l = last;
    if (l == null)//如果尾节点为空，表示当前集合为空，抛出异常
        throw new NoSuchElementException();
    return unlinkLast(l);
}

private E unlinkLast(Node<E> l) {
    // assert l == last && l != null;
    final E element = l.item;
    final Node<E> prev = l.prev;
    l.item = null;
    l.prev = null;     //将节点的元素以及引用都设为 null，便于垃圾回收
    last = prev;       //尾节点为倒数第二个节点
    if (prev == null)  //如果倒数第二个节点为null
        first = null;  //那么将节点也置为 null
    else
        prev.next = null;//如果倒数第二个节点不为空，那么将倒数第二个节点的下一个引用置为 null
    size--;
    modCount++;
    return element;
}
```

****

### remove(int index)

****

删除此列表中指定位置的元素：

```java
//删除此列表中指定位置的元素
public E remove(int index) {
    //判断索引 index >= 0 && index <= size中时抛出IndexOutOfBoundsException异常
    checkElementIndex(index);
    return unlink(node(index));
}
E unlink(Node<E> x) {
    // assert x != null;
    final E element = x.item;
    final Node<E> next = x.next;
    final Node<E> prev = x.prev;

    if (prev == null) { //如果删除节点位置的上一个节点引用为null（表示删除第一个元素）
        first = next;       //将头结点置为第一个元素的下一个节点
    } else {            //如果删除节点位置的上一个节点引用不为null
        prev.next = next;   //将删除节点的上一个节点的下一个节点引用指向删除节点的下一个节点（去掉删除节点）
        x.prev = null;      //删除节点的上一个节点引用置为null
    }

    if (next == null) {  //如果删除节点的下一个节点引用为null（表示删除最后一个节点）
        last = prev;         //将尾节点置为删除节点的上一个节点
    } else {             //不是删除尾节点
        next.prev = prev;    //将删除节点的下一个节点的上一个节点的引用指向删除节点的上一个节点
        x.next = null;       //将删除节点的下一个节点引用置为null
    }

    x.item = null;//删除节点内容置为null，便于垃圾回收
    size--;
    modCount++;
    return element;
}
```

****

## 遍历集合

****

### 普通 for 循环

****

```java
LinkedList<String> linkedList = new LinkedList<>();
linkedList.add("L");
linkedList.add("Y");
linkedList.add("S");

for(int i = 0 ; i < linkedList.size(); i ++){
    System.out.print(linkedList.get(i) + " ");  //L Y S
}
```

**注意**：

- 利用 LinkedList 的 get(int index) 方法，遍历出所有的元素
- 但是 get(int index) 方法每次都要遍历该索引之前的所有元素，效率极低

****

### 迭代器

****

在LinkedList中除了有一个Node的内部类外，应该还能看到另外两个内部类，那就是ListItr，还有一个是DescendingIterator。

ListItr内部类:

```java
private class ListItr implements ListIterator<E> 
```

看一下他的继承结构，发现只继承了一个ListIterator，到ListIterator中一看：

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220221161618682.png)

其中不止有向后迭代的方法，还有向前迭代的方法，可以让linkedList不光能像后迭代，也能向前迭代

看一下ListItr中的方法，可以发现，在迭代的过程中，还能移除、修改、添加值得操作

![](https://lys2021.com/wp-content/uploads/2024/10/image-20220221161652319.png)

其中 `DescendingIterator` 内部类：　

```java
/**
* Adapter to provide descending iterators via ListItr.previous
*/
private class DescendingIterator implements Iterator<E> {
    private final ListItr itr = new ListItr(size());
    public boolean hasNext() {
        return itr.hasPrevious();
    }
    public E next() {
        return itr.previous();
    }
    public void remove() {
        itr.remove();
    }
}
```

DescendingIterator 通过调用 ListItr，作用是封装一下Itr中几个方法，让使用者以正常的思维去写代码

例如，在从后往前遍历的时候，也是跟从前往后遍历一样，使用next等操作，而不用使用特殊的previous

```java
LinkedList<String> linkedList = new LinkedList<>();
linkedList.add("A");
linkedList.add("B");
linkedList.add("C");
linkedList.add("D");


Iterator<String> listIt = linkedList.listIterator();
while(listIt.hasNext()){
    System.out.print(listIt.next()+" ");//A B C D
}

//通过适配器模式实现的接口，作用是倒序打印链表
Iterator<String> it = linkedList.descendingIterator();
while(it.hasNext()){
    System.out.print(it.next() + " ");//D C B A
}
```

****

### 迭代器和for循环效率差异

****

```java
LinkedList<Integer> linkedList = new LinkedList<>();
for (int i = 0; i < 10000; i ++) {
    linkedList.add(i);
}

long beginTimeFor = System.currentTimeMillis();
for (int i = 0; i < 10000; i ++) {
    System.out.println(linkedList.get(i));
}
long endTimeFor = System.currentTimeMillis();
System.out.println("使用普通for循环遍历10000个元素需要的时间：" + (endTimeFor - beginTimeFor));


long beginTimeIte = System.currentTimeMillis();
Iterator<Integer> it = linkedList.listIterator();
while (it.hasNext()) {
    System.out.print(it.next() + " ");
}
long endTimeIte = System.currentTimeMillis();
System.out.println("使用迭代器遍历10000个元素需要的时间：" + (endTimeIte - beginTimeIte));
```

一万个元素两者之间都相差一倍多的时间，如果是十万，百万个元素，那么两者之间相差的速度会越来越大，因此推荐使用迭代器遍历 LinkedList。

****
