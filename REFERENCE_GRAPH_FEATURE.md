# 🕸️ Reference Graph Feature

## Overview

The **Reference Graph Feature** creates an interactive visualization of academic paper references, allowing you to:

- **Visualize reference relationships** between papers
- **Navigate through academic networks** up to 2 levels deep
- **Click on any paper** to open it and enable chatbot interaction
- **Process papers on-demand** for immediate chatbot access

## 🎯 How It Works

### 1. **Root Node (Level 0)**
- Your **uploaded paper** becomes the center of the graph
- Displayed as a **red node** with larger size

### 2. **Children (Level 1)**
- **References** from your paper become child nodes
- Displayed as **teal nodes** with medium size
- Only papers with **accessible content** are included

### 3. **Grandchildren (Level 2)**
- **References of references** become grandchild nodes
- Displayed as **blue nodes** with smaller size
- **Maximum depth limited to 2** to prevent infinite recursion

## 🚀 Features

### **Interactive Visualization**
- **Hover tooltips** showing paper details
- **Clickable nodes** to select papers
- **Dynamic layout** with physics simulation
- **Color-coded levels** for easy identification

### **Paper Integration**
- **Seamless paper viewing** from graph nodes
- **On-demand processing** for papers without embeddings
- **Chatbot integration** for any processed paper
- **Real-time status updates**

### **Smart Content Detection**
- **Automatic filtering** of papers without content
- **Content availability indicators** on each node
- **Processing status** for papers needing RAG setup

## 📱 How to Use

### **1. Access the Reference Graph**
```
Paper Detail Page → "Reference Graph" Button
```

### **2. Build the Graph**
- Click **"Build Reference Graph"** button
- System automatically discovers references
- Graph renders with interactive nodes

### **3. Navigate the Graph**
- **Hover** over nodes to see details
- **Click** on any node to select it
- **Right panel** shows paper information and chat

### **4. Interact with Papers**
- **View paper details** and status
- **Process papers** that need RAG setup
- **Chat with papers** using the integrated chatbot

## 🔧 Technical Implementation

### **Backend Components**

#### **ReferenceGraphBuilder Class**
```python
class ReferenceGraphBuilder:
    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth
        self.visited_papers = set()
        self.graph_data = {'nodes': [], 'edges': []}
    
    def build_graph(self, root_paper: Paper) -> Dict:
        # Builds hierarchical reference graph
        # Limits depth to prevent infinite recursion
```

#### **API Endpoints**
- `GET /api/papers/{id}/reference-graph/` - Build reference graph
- `GET /api/papers/{id}/details/` - Get paper details for interaction
- `POST /api/papers/{id}/process-rag/` - Process paper for chatbot

### **Frontend Components**

#### **Interactive Graph**
- **vis.js Network** for graph visualization
- **Responsive design** with mobile support
- **Real-time updates** and status indicators

#### **Chat Integration**
- **Side-by-side layout** with graph and chat
- **Paper selection** from graph nodes
- **Processing workflow** for unprocessed papers

## 📊 Graph Structure

### **Node Properties**
```json
{
  "id": "paper-uuid",
  "label": "Truncated Title...",
  "title": "Full Paper Title",
  "author": "Author Name",
  "group": "root|children|grandchildren",
  "color": "#FF6B6B|#4ECDC4|#45B7D1",
  "size": 30|25|20,
  "level": 0|1|2,
  "has_content": true|false,
  "chunks_count": 15,
  "embeddings_count": 15
}
```

### **Edge Properties**
```json
{
  "from": "source-paper-uuid",
  "to": "target-paper-uuid",
  "arrows": "to",
  "label": "references",
  "width": 2,
  "color": "#666666"
}
```

## 🎨 Visual Design

### **Color Scheme**
- **🔴 Root (Level 0)**: `#FF6B6B` - Red
- **🟢 Children (Level 1)**: `#4ECDC4` - Teal  
- **🔵 Grandchildren (Level 2)**: `#45B7D1` - Blue

### **Node Sizing**
- **Root**: 30px - Largest, most prominent
- **Children**: 25px - Medium, clearly visible
- **Grandchildren**: 20px - Smaller, secondary importance

### **Interactive Elements**
- **Hover effects** with detailed tooltips
- **Click feedback** with visual selection
- **Smooth animations** for better UX

## 🔍 Use Cases

### **Academic Research**
- **Literature review** visualization
- **Citation network** analysis
- **Research gap** identification

### **Paper Discovery**
- **Related work** exploration
- **Author network** mapping
- **Research trend** analysis

### **Collaborative Research**
- **Team paper** organization
- **Reference sharing** and discussion
- **Research progress** tracking

## 🚧 Limitations & Considerations

### **Depth Limitation**
- **Maximum depth: 2 levels** to prevent infinite recursion
- **Performance optimization** for large reference networks
- **Memory management** for complex graphs

### **Content Requirements**
- **Papers must have content** to appear in graph
- **Processing required** for chatbot functionality
- **Automatic filtering** of inaccessible papers

### **Network Performance**
- **Large graphs** may impact rendering performance
- **Reference discovery** depends on paper processing
- **Real-time updates** may have slight delays

## 🛠️ Troubleshooting

### **Common Issues**

#### **Graph Not Building**
- Check if paper has references
- Verify paper processing status
- Check console for error messages

#### **Nodes Not Clickable**
- Ensure paper has content
- Check if paper is processed
- Verify API endpoint accessibility

#### **Chatbot Not Working**
- Process paper with RAG engine
- Check embedding generation status
- Verify chatbot API configuration

### **Debug Commands**
```bash
# Test reference graph for specific paper
python manage.py test_reference_graph --paper-id <uuid>

# Check paper processing status
python manage.py check_papers --paper-id <uuid> --detailed

# Rebuild embeddings for paper
python manage.py rebuild_embeddings --paper-id <uuid>
```

## 🔮 Future Enhancements

### **Planned Features**
- **Export functionality** for graph data
- **Advanced filtering** by paper type/date
- **Collaborative annotations** on graph nodes
- **Integration** with external citation databases

### **Performance Improvements**
- **Lazy loading** for large graphs
- **Caching** of reference data
- **Optimized rendering** for mobile devices

## 📚 Related Documentation

- [Vector Embeddings Guide](VECTOR_EMBEDDINGS_GUIDE.md)
- [Chatbot Integration](README.md#chatbot-features)
- [Paper Processing](README.md#paper-processing)
- [API Reference](README.md#api-endpoints)

---

**🎉 The Reference Graph Feature transforms your academic paper collection into an interactive, navigable network of knowledge!**
