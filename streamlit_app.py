import React, { useState, useEffect, useMemo } from 'react';
import { ShoppingCart, Package, DollarSign, BarChart2, Plus, X, List, Trash2, Users, Loader, Coffee, AlertTriangle } from 'lucide-react';

// --- FIREBASE IMPORTS ---
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, setDoc, onSnapshot } from 'firebase/firestore';

// --- CONFIGURACIONES (Variables globales del entorno) ---
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : null;

// Constantes de diseño
const ACCENT_COLOR_HEX = '#279aa0';
const PRIMARY_COLOR_BG = `bg-[${ACCENT_COLOR_HEX}]`;
const PRIMARY_TEXT_COLOR = `text-[${ACCENT_COLOR_HEX}]`;
const PRIMARY_HOVER_BG = 'hover:bg-[#1a7478]';
const ACCENT_BG_LIGHT = 'bg-[#f0f9f9]';

const initialProducts = [
  { id: 101, name: 'Entrada', price: 2000.00, stock: 500 },
];

const initialAccounts = [
  { id: Date.now(), name: 'Venta 1', items: [], time: Date.now() },
];

// --- COMPONENTE LOGO ---
const Logo = () => {
    const logoImageUrl = "https://www.fecobacr.com/wp-content/uploads/2025/06/LSB-Metropoli.jpg";
    return (
        <div className="flex items-center space-x-2 p-4">
            <img 
                src={logoImageUrl} 
                alt="MBA Cafe Logo" 
                className="w-10 h-10 object-contain rounded-full border-2 border-white shadow-md"
                onError={(e) => {
                    e.target.style.display = 'none'; 
                    e.target.parentNode.innerHTML += '<span class="text-white font-black">MBA</span>';
                }}
            />
            <h1 className="text-xl font-black text-white leading-tight">MBA Cafe</h1>
        </div>
    );
};

// --- MODAL REUTILIZABLE ---
const Modal = ({ title, onClose, children }) => (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center border-b pb-3 mb-4">
          <h3 className="text-xl font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <X className="w-6 h-6" />
          </button>
        </div>
        {children}
      </div>
    </div>
);

export const App = () => {
  const [db, setDb] = useState(null);
  const [userId, setUserId] = useState(null);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [products, setProducts] = useState(initialProducts);
  const [salesHistory, setSalesHistory] = useState([]);
  const [openAccounts, setOpenAccounts] = useState(initialAccounts);
  const [activeAccountId, setActiveAccountId] = useState(initialAccounts[0]?.id || null);
  const [lastSaleNumber, setLastSaleNumber] = useState(0);

  const [activeTab, setActiveTab] = useState('pos');
  const [saleMessage, setSaleMessage] = useState('');
  const [inventoryMessage, setInventoryMessage] = useState('');
  const [reportMessage, setReportMessage] = useState('');
  const [newAccountName, setNewAccountName] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: '', price: '', stock: '' });
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // --- FIREBASE INITIALIZATION ---
  useEffect(() => {
    if (!firebaseConfig) {
      setIsLoading(false);
      return;
    }
    const app = initializeApp(firebaseConfig);
    const dbInstance = getFirestore(app);
    const authInstance = getAuth(app);
    setDb(dbInstance);

    const authUnsubscribe = onAuthStateChanged(authInstance, async (user) => {
        if (user) {
            setUserId(user.uid);
        } else {
            try {
                let currentUserId;
                if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
                    const credentials = await signInWithCustomToken(authInstance, __initial_auth_token);
                    currentUserId = credentials.user.uid;
                } else {
                    const anonymousUser = await signInAnonymously(authInstance);
                    currentUserId = anonymousUser.user.uid;
                }
                setUserId(currentUserId);
            } catch (error) {
                setUserId(crypto.randomUUID());
            }
        }
        setIsAuthReady(true);
    });
    return () => authUnsubscribe();
  }, [firebaseConfig]);

  // --- FIRESTORE DATA LISTENER ---
  useEffect(() => {
      if (!db || !userId || !isAuthReady) return; 
      const docRef = doc(db, 'artifacts', appId, 'users', userId, 'pos_data', 'appState');
      const unsubscribe = onSnapshot(docRef, (docSnapshot) => {
          if (docSnapshot.exists()) {
              const data = docSnapshot.data();
              setProducts(data.products || initialProducts);
              setSalesHistory(data.salesHistory || []);
              setOpenAccounts(data.openAccounts || initialAccounts);
              setLastSaleNumber(data.lastSaleNumber || 0); 
              setActiveAccountId(data.activeAccountId || data.openAccounts?.[0]?.id || null);
          } else {
              saveInitialData(docRef);
          }
          setIsLoading(false);
      }, (error) => {
          setIsLoading(false);
          setSaleMessage(`ERROR: ${error.code}`);
      });
      return () => unsubscribe();
  }, [db, userId, isAuthReady]);

  const saveStateToFirestore = async (updates = {}) => {
    if (!db || !userId) return;
    const stateToSave = {
        products: updates.products !== undefined ? updates.products : products,
        salesHistory: updates.salesHistory !== undefined ? updates.salesHistory : salesHistory,
        openAccounts: updates.openAccounts !== undefined ? updates.openAccounts : openAccounts,
        activeAccountId: updates.activeAccountId !== undefined ? updates.activeAccountId : activeAccountId,
        lastSaleNumber: updates.lastSaleNumber !== undefined ? updates.lastSaleNumber : lastSaleNumber,
    };
    const docRef = doc(db, 'artifacts', appId, 'users', userId, 'pos_data', 'appState');
    try {
        await setDoc(docRef, stateToSave);
    } catch (e) {
        setSaleMessage(`ERROR: ${e.message}`);
        clearMessages(setSaleMessage);
    }
  };

  const saveInitialData = async (docRef) => {
    const initialData = {
        products: initialProducts,
        salesHistory: [],
        openAccounts: initialAccounts,
        activeAccountId: initialAccounts[0]?.id || null,
        lastSaleNumber: 1,
    };
    try { await setDoc(docRef, initialData); } catch (e) { console.error(e); }
  };

  const clearMessages = (setter) => setTimeout(() => setter(''), 4000);

  const activeAccount = useMemo(() => openAccounts.find(acc => acc.id === activeAccountId), [openAccounts, activeAccountId]);
  const currentCart = activeAccount?.items || [];
  
  const calculateTotals = useMemo(() => {
    const subtotal = currentCart.reduce((acc, item) => acc + item.price * item.quantity, 0);
    return { subtotal, total: subtotal };
  }, [currentCart]);

  // --- LOGICA DE CUENTAS ---
  const addAccount = (name) => {
    if (isLoading) return;
    let finalName = name.trim();
    let newLastSaleNumber = lastSaleNumber;
    if (!finalName || finalName.toLowerCase().startsWith('venta')) {
        newLastSaleNumber = lastSaleNumber + 1;
        finalName = `Venta ${newLastSaleNumber}`;
    }
    const newId = Date.now();
    const newAccounts = [...openAccounts, { id: newId, name: finalName, items: [], time: newId }];
    saveStateToFirestore({ openAccounts: newAccounts, activeAccountId: newId, lastSaleNumber: newLastSaleNumber });
  };

  const closeAccountWithoutSale = (id) => {
    const remainingAccounts = openAccounts.filter(acc => acc.id !== id);
    let nextActiveId = activeAccountId === id ? (remainingAccounts[0]?.id || null) : activeAccountId;
    saveStateToFirestore({ openAccounts: remainingAccounts, activeAccountId: nextActiveId });
  };

  // --- LOGICA TPV ---
  const addToCart = (product) => {
    if (isLoading || !activeAccount) return;
    const productInStock = products.find(p => p.id === product.id);
    if (!productInStock || productInStock.stock <= 0) return;

    const updatedAccounts = openAccounts.map(account => {
      if (account.id === activeAccountId) {
        const existingItem = account.items.find(item => item.id === product.id);
        const updatedItems = existingItem 
          ? account.items.map(item => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
          : [...account.items, { ...product, quantity: 1 }];
        return { ...account, items: updatedItems };
      }
      return account;
    });
    saveStateToFirestore({ openAccounts: updatedAccounts });
  };

  const removeFromCart = (productId) => {
    const updatedAccounts = openAccounts.map(account => {
      if (account.id === activeAccountId) {
        const item = account.items.find(i => i.id === productId);
        const updatedItems = item && item.quantity > 1
          ? account.items.map(i => i.id === productId ? { ...i, quantity: i.quantity - 1 } : i)
          : account.items.filter(i => i.id !== productId);
        return { ...account, items: updatedItems };
      }
      return account;
    });
    saveStateToFirestore({ openAccounts: updatedAccounts });
  };

  const completeSale = (paymentMethod) => { 
    if (isLoading || currentCart.length === 0 || !activeAccount) return;
    const { total } = calculateTotals;
    const newSale = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString('es-ES'),
      date: new Date().toLocaleDateString('es-ES'),
      accountName: activeAccount.name, 
      items: currentCart,
      total: total,
      payment: paymentMethod,
    };
    const updatedProducts = products.map(p => {
        const item = currentCart.find(i => i.id === p.id);
        return item ? { ...p, stock: Math.max(0, p.stock - item.quantity) } : p;
    });
    const remainingAccounts = openAccounts.filter(acc => acc.id !== activeAccountId);
    saveStateToFirestore({
        salesHistory: [newSale, ...salesHistory],
        products: updatedProducts,
        openAccounts: remainingAccounts,
        activeAccountId: remainingAccounts[0]?.id || null,
    });
    setSaleMessage(`Venta completada: ₡${total.toFixed(2)}`);
    clearMessages(setSaleMessage);
  };

  // --- LOGICA INVENTARIO ---
  const updatePrice = (productId, newPrice) => {
    const updated = products.map(p => p.id === productId ? { ...p, price: parseFloat(newPrice) } : p);
    saveStateToFirestore({ products: updated });
  };
  
  const updateStockDirectly = (productId, newStock) => {
    const updated = products.map(p => p.id === productId ? { ...p, stock: parseInt(newStock) } : p);
    saveStateToFirestore({ products: updated });
  };

  const confirmDeleteProduct = (name) => {
    if (name.trim() === productToDelete.name.trim()) {
      saveStateToFirestore({ products: products.filter(p => p.id !== productToDelete.id) });
      setIsDeleteModalOpen(false);
    }
  };

  // --- COMPONENTE FILA PRODUCTO (Mejorado) ---
  const ProductRow = React.memo(({ product, isLoading, updatePrice, updateStockDirectly, openDeleteModal }) => {
    const [editPrice, setEditPrice] = useState(product.price.toFixed(2));
    const [editStock, setEditStock] = useState(product.stock.toString());

    useEffect(() => {
        // Sincroniza con la DB solo si el input no tiene el foco
        if (document.activeElement !== document.getElementById(`price-${product.id}`)) {
            setEditPrice(product.price.toFixed(2));
        }
        if (document.activeElement !== document.getElementById(`stock-${product.id}`)) {
            setEditStock(product.stock.toString());
        }
    }, [product.price, product.stock, product.id]);

    return (
        <tr className="hover:bg-gray-50">
            <td className="px-6 py-4 font-medium text-gray-900"><Coffee className="inline w-4 h-4 mr-2" />{product.name}</td>
            <td className="px-6 py-4 text-sm text-gray-500">{product.id}</td>
            <td className="px-6 py-4">
                <input
                    id={`price-${product.id}`}
                    type="text"
                    value={editPrice}
                    onChange={(e) => setEditPrice(e.target.value.replace(/[^0-9.]/g, ''))}
                    onBlur={() => updatePrice(product.id, editPrice)}
                    className="w-24 p-1 border rounded"
                    disabled={isLoading}
                />
            </td>
            <td className="px-6 py-4">
                <input
                    id={`stock-${product.id}`}
                    type="text"
                    value={editStock}
                    onChange={(e) => setEditStock(e.target.value.replace(/[^0-9]/g, ''))}
                    onBlur={() => updateStockDirectly(product.id, editStock)}
                    className={`w-20 p-1 border rounded text-center ${product.stock <= 5 ? 'bg-red-100' : ''}`}
                    disabled={isLoading}
                />
            </td>
            <td className="px-6 py-4 text-center">
                <button onClick={() => openDeleteModal(product)} className="text-red-600 hover:bg-red-50 p-2 rounded-full"><Trash2 className="w-5 h-5" /></button>
            </td>
        </tr>
    );
  });

  // --- RENDERIZADO DE VISTAS ---
  const renderPOS = () => (
    <div className="flex flex-col lg:flex-row h-full">
      <div className="lg:w-1/4 p-4 border-r bg-white flex flex-col h-full overflow-y-auto">
          <h2 className="text-xl font-bold mb-4 flex items-center"><Users className="w-5 h-5 mr-2" /> Pedidos</h2>
          <form onSubmit={(e) => { e.preventDefault(); addAccount(newAccountName); setNewAccountName(''); }} className="mb-4 p-3 rounded-xl border" style={{backgroundColor: '#279aa01a'}}>
              <input type="text" placeholder="Nombre del pedido" value={newAccountName} onChange={(e) => setNewAccountName(e.target.value)} className="w-full p-2 mb-2 border rounded-lg text-sm" />
              <button type="submit" className={`w-full py-2 ${PRIMARY_COLOR_BG} text-white rounded-lg font-bold`}>Nuevo Pedido</button>
          </form>
          <div className="space-y-2">
              {openAccounts.map(acc => (
                  <div key={acc.id} onClick={() => saveStateToFirestore({ activeAccountId: acc.id })} className={`p-3 rounded-xl cursor-pointer ${activeAccountId === acc.id ? 'bg-[#279aa0] text-white shadow-lg' : 'bg-gray-100'}`}>
                      <div className="flex justify-between items-center">
                          <span className="font-bold">{acc.name}</span>
                          <X onClick={(e) => { e.stopPropagation(); closeAccountWithoutSale(acc.id); }} className="w-4 h-4 hover:text-red-300" />
                      </div>
                  </div>
              ))}
          </div>
      </div>

      <div className="lg:w-2/4 p-4 border-r overflow-y-auto">
        <h1 className="text-2xl font-bold mb-4">{activeAccount?.name || 'Seleccione Cuenta'}</h1>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase())).map(product => (
                <button key={product.id} onClick={() => addToCart(product)} disabled={product.stock <= 0} className={`p-4 rounded-xl border text-left transition ${product.stock > 0 ? 'hover:bg-[#279aa0] hover:text-white bg-white' : 'bg-gray-100 opacity-50'}`}>
                    <p className="font-bold">{product.name}</p>
                    {/* PALABRA "STOCK" ELIMINADA AQUÍ  */}
                    <p className="text-sm opacity-80">{product.stock} disponibles</p> 
                    <p className="text-xl font-black mt-2">₡{product.price.toFixed(2)}</p>
                </button>
            ))}
        </div>
      </div>

      <div className="lg:w-1/4 p-4 bg-gray-50 flex flex-col">
          <h2 className="text-xl font-bold mb-4 flex items-center"><ShoppingCart className="w-5 h-5 mr-2" /> Carrito</h2>
          <div className="flex-grow bg-white rounded-xl p-2 shadow-inner overflow-y-auto mb-4">
              {currentCart.map(item => (
                  <div key={item.id} className="flex justify-between items-center border-b py-2 text-sm">
                      <div><p className="font-bold">{item.name}</p><p>₡{item.price} x {item.quantity}</p></div>
                      <X onClick={() => removeFromCart(item.id)} className="w-4 h-4 text-red-500 cursor-pointer" />
                  </div>
              ))}
          </div>
          <div className="bg-white p-4 rounded-xl shadow-md mb-4">
              <div className="flex justify-between text-2xl font-black"><span>TOTAL:</span><span>₡{calculateTotals.total.toFixed(2)}</span></div>
          </div>
          <button onClick={() => completeSale('Efectivo')} className="w-full py-3 bg-green-600 text-white rounded-xl font-bold mb-2">Pagar Efectivo</button>
          <button onClick={() => completeSale('SINPE')} className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold">Pagar SINPE</button>
      </div>
    </div>
  );

  const renderInventory = () => (
    <div className="p-4 overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold flex items-center"><Package className="w-6 h-6 mr-2" /> Inventario</h1>
        <button onClick={() => setIsModalOpen(true)} className={`px-4 py-2 ${PRIMARY_COLOR_BG} text-white rounded-xl font-bold`}>+ Añadir</button>
      </div>
      <input type="text" placeholder="Buscar..." onChange={(e) => setSearchTerm(e.target.value)} className="w-full p-3 mb-4 border rounded-xl" />
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-100">
            <tr><th className="px-6 py-3 text-left text-xs">Nombre</th><th className="px-6 py-3 text-left text-xs">ID</th><th className="px-6 py-3 text-left text-xs">Precio</th><th className="px-6 py-3 text-left text-xs">Stock</th><th className="px-6 py-3">Acciones</th></tr>
          </thead>
          <tbody className="divide-y">
            {products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase())).map(p => (
                <ProductRow key={p.id} product={p} isLoading={isLoading} updatePrice={updatePrice} updateStockDirectly={updateStockDirectly} openDeleteModal={(p) => { setProductToDelete(p); setIsDeleteModalOpen(true); }} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      <div className={`w-20 md:w-64 flex flex-col ${PRIMARY_COLOR_BG} shadow-2xl`}>
        <Logo />
        <nav className="flex-grow mt-8 p-2 space-y-2">
          {[
            { id: 'pos', name: 'Ventas', icon: ShoppingCart },
            { id: 'inventory', name: 'Inventario', icon: Package },
            { id: 'reports', name: 'Reportes', icon: BarChart2 }
          ].map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center w-full py-3 px-4 rounded-xl text-white ${activeTab === tab.id ? 'bg-white !text-[#279aa0] font-bold shadow-lg' : 'hover:bg-[#1a7478]'}`}>
              <tab.icon className="w-5 h-5 md:mr-3" /><span className="hidden md:inline">{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>
      <main className="flex-grow overflow-hidden">
        {activeTab === 'pos' && renderPOS()}
        {activeTab === 'inventory' && renderInventory()}
      </main>
      {isDeleteModalOpen && (
          <Modal title="Eliminar Producto" onClose={() => setIsDeleteModalOpen(false)}>
              <p>Escribe <strong>{productToDelete?.name}</strong> para confirmar:</p>
              <input type="text" onChange={(e) => confirmDeleteProduct(e.target.value)} className="w-full p-2 border rounded mt-2" />
          </Modal>
      )}
    </div>
  );
};

export default App;
