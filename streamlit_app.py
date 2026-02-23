import React, { useState, useEffect, useMemo } from 'react';
import { ShoppingCart, Package, DollarSign, BarChart2, Plus, X, List, Trash2, Users, Loader, Coffee, AlertTriangle } from 'lucide-react';

// --- FIREBASE IMPORTS ---
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, setDoc, onSnapshot } from 'firebase/firestore';

// --- CONFIGURACIONES ---
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : null;

const ACCENT_COLOR_HEX = '#279aa0';
const PRIMARY_COLOR_BG = `bg-[${ACCENT_COLOR_HEX}]`;

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
                alt="Logo" 
                className="w-10 h-10 object-contain rounded-full border-2 border-white shadow-md"
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
  const [newAccountName, setNewAccountName] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: '', price: '', stock: '' });
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // --- FIREBASE LOGIC ---
  useEffect(() => {
    if (!firebaseConfig) { setIsLoading(false); return; }
    const app = initializeApp(firebaseConfig);
    const dbInstance = getFirestore(app);
    const authInstance = getAuth(app);
    setDb(dbInstance);

    const authUnsubscribe = onAuthStateChanged(authInstance, async (user) => {
        if (user) { setUserId(user.uid); } 
        else {
            try {
                const anonymousUser = await signInAnonymously(authInstance);
                setUserId(anonymousUser.user.uid);
            } catch (error) { setUserId(crypto.randomUUID()); }
        }
        setIsAuthReady(true);
    });
    return () => authUnsubscribe();
  }, [firebaseConfig]);

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
          } else { saveInitialData(docRef); }
          setIsLoading(false);
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
    try { await setDoc(doc(db, 'artifacts', appId, 'users', userId, 'pos_data', 'appState'), stateToSave); } 
    catch (e) { console.error(e); }
  };

  const saveInitialData = async (docRef) => {
    const initialData = { products: initialProducts, salesHistory: [], openAccounts: initialAccounts, activeAccountId: initialAccounts[0]?.id || null, lastSaleNumber: 1 };
    try { await setDoc(docRef, initialData); } catch (e) { console.error(e); }
  };

  const activeAccount = useMemo(() => openAccounts.find(acc => acc.id === activeAccountId), [openAccounts, activeAccountId]);
  const currentCart = activeAccount?.items || [];
  
  const calculateTotals = useMemo(() => {
    const total = currentCart.reduce((acc, item) => acc + item.price * item.quantity, 0);
    return { total };
  }, [currentCart]);

  const addAccount = (name) => {
    let finalName = name.trim();
    let newLastSaleNumber = lastSaleNumber;
    if (!finalName) {
        newLastSaleNumber = lastSaleNumber + 1;
        finalName = 'Venta ' + newLastSaleNumber;
    }
    const newId = Date.now();
    const newAccounts = [...openAccounts, { id: newId, name: finalName, items: [], time: newId }];
    saveStateToFirestore({ openAccounts: newAccounts, activeAccountId: newId, lastSaleNumber: newLastSaleNumber });
  };

  const addToCart = (product) => {
    if (!activeAccount) return;
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

  const completeSale = (paymentMethod) => { 
    if (currentCart.length === 0 || !activeAccount) return;
    const { total } = calculateTotals;
    const newSale = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
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
    setSaleMessage('Venta guardada');
    setTimeout(() => setSaleMessage(''), 3000);
  };

  // --- COMPONENTE FILA PRODUCTO ---
  const ProductRow = ({ product, updatePrice, updateStockDirectly, openDeleteModal }) => {
    const [editPrice, setEditPrice] = useState(product.price.toString());
    const [editStock, setEditStock] = useState(product.stock.toString());

    useEffect(() => {
        if (document.activeElement !== document.getElementById('price-' + product.id)) {
            setEditPrice(product.price.toString());
        }
        if (document.activeElement !== document.getElementById('stock-' + product.id)) {
            setEditStock(product.stock.toString());
        }
    }, [product.price, product.stock]);

    return (
        <tr className="hover:bg-gray-50">
            <td className="px-6 py-4 font-medium"><Coffee className="inline w-4 h-4 mr-2" />{product.name}</td>
            <td className="px-6 py-4">
                <input
                    id={'price-' + product.id}
                    type="number"
                    value={editPrice}
                    onChange={(e) => setEditPrice(e.target.value)}
                    onBlur={() => updatePrice(product.id, parseFloat(editPrice))}
                    className="w-24 p-1 border rounded"
                />
            </td>
            <td className="px-6 py-4">
                <input
                    id={'stock-' + product.id}
                    type="number"
                    value={editStock}
                    onChange={(e) => setEditStock(e.target.value)}
                    onBlur={() => updateStockDirectly(product.id, parseInt(editStock))}
                    className="w-20 p-1 border rounded"
                />
            </td>
            <td className="px-6 py-4 text-center">
                <button onClick={() => openDeleteModal(product)} className="text-red-600 p-2"><Trash2 className="w-5 h-5" /></button>
            </td>
        </tr>
    );
  };

  const renderPOS = () => (
    <div className="flex flex-col lg:flex-row h-full">
      <div className="lg:w-1/4 p-4 border-r bg-white flex flex-col overflow-y-auto">
          <h2 className="text-xl font-bold mb-4 flex items-center"><Users className="w-5 h-5 mr-2" /> Pedidos</h2>
          <form onSubmit={(e) => { e.preventDefault(); addAccount(newAccountName); setNewAccountName(''); }} className="mb-4">
              <input type="text" placeholder="Nuevo pedido..." value={newAccountName} onChange={(e) => setNewAccountName(e.target.value)} className="w-full p-2 mb-2 border rounded-lg" />
              <button type="submit" className={`w-full py-2 ${PRIMARY_COLOR_BG} text-white rounded-lg font-bold`}>Agregar</button>
          </form>
          <div className="space-y-2">
              {openAccounts.map(acc => (
                  <div key={acc.id} onClick={() => saveStateToFirestore({ activeAccountId: acc.id })} className={`p-3 rounded-xl cursor-pointer ${activeAccountId === acc.id ? 'bg-[#279aa0] text-white' : 'bg-gray-100'}`}>
                      <div className="flex justify-between items-center">
                          <span className="font-bold">{acc.name}</span>
                          <X onClick={(e) => { e.stopPropagation(); saveStateToFirestore({ openAccounts: openAccounts.filter(a => a.id !== acc.id) }); }} className="w-4 h-4" />
                      </div>
                  </div>
              ))}
          </div>
      </div>

      <div className="lg:w-2/4 p-4 border-r overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-bold">{activeAccount?.name || 'Seleccione Cuenta'}</h1>
            {saleMessage && <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm animate-bounce">{saleMessage}</span>}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {products.map(product => (
                <button key={product.id} onClick={() => addToCart(product)} className="p-4 rounded-xl border text-left hover:bg-[#279aa0] hover:text-white transition bg-white">
                    <p className="font-bold">{product.name}</p>
                    <p className="text-sm opacity-80">{product.stock} disponibles</p> 
                    <p className="text-xl font-black mt-2">C{product.price}</p>
                </button>
            ))}
        </div>
      </div>

      <div className="lg:w-1/4 p-4 bg-gray-50 flex flex-col">
          <h2 className="text-xl font-bold mb-4 flex items-center"><ShoppingCart className="w-5 h-5 mr-2" /> Carrito</h2>
          <div className="flex-grow bg-white rounded-xl p-2 shadow-inner overflow-y-auto mb-4">
              {currentCart.map(item => (
                  <div key={item.id} className="flex justify-between items-center border-b py-2 text-sm">
                      <div><p className="font-bold">{item.name}</p><p>C{item.price} x {item.quantity}</p></div>
                      <X onClick={() => saveStateToFirestore({ openAccounts: openAccounts.map(a => a.id === activeAccountId ? {...a, items: a.items.filter(i => i.id !== item.id)} : a) })} className="w-4 h-4 text-red-500 cursor-pointer" />
                  </div>
              ))}
          </div>
          <div className="bg-white p-4 rounded-xl shadow-md mb-4">
              <div className="flex justify-between text-2xl font-black"><span>TOTAL:</span><span>C{calculateTotals.total}</span></div>
          </div>
          <button onClick={() => completeSale('Efectivo')} className="w-full py-3 bg-green-600 text-
