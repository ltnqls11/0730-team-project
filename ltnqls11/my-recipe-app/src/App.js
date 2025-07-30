import React, { useState, useEffect } from 'react';

// Tailwind CSS CDN (HTML 파일의 <head>에 포함되어 있다고 가정)
// <script src="https://cdn.tailwindcss.com"></script>

function App() {
  // --- 상태 관리 ---
  const [isLoggedIn, setIsLoggedIn] = useState(false); // 로그인 상태
  const [token, setToken] = useState(localStorage.getItem('jwtToken') || ''); // JWT 토큰
  const [userId, setUserId] = useState(localStorage.getItem('userId') || ''); // 사용자 ID
  const [username, setUsername] = useState(''); // 사용자 이름 (로그인/회원가입 폼)
  const [password, setPassword] = useState(''); // 비밀번호 (로그인/회원가입 폼)
  const [email, setEmail] = useState(''); // 이메일 (회원가입 폼)
  const [message, setMessage] = useState(''); // 사용자에게 보여줄 메시지 (성공/에러)
  const [currentView, setCurrentView] = useState('login'); // 현재 뷰 ('login', 'dashboard', 'addIngredient', 'recommend')

  // 재료 관리 관련 상태
  const [ingredients, setIngredients] = useState([]); // 사용자의 보유 재료 목록
  const [newIngredientName, setNewIngredientName] = useState('');
  const [newIngredientQuantity, setNewIngredientQuantity] = useState('');
  const [newIngredientPurchaseDate, setNewIngredientPurchaseDate] = useState('');
  const [newIngredientExpirationDate, setNewIngredientExpirationDate] = useState('');
  const [newIngredientLocation, setNewIngredientLocation] = useState('냉장실');

  // 레시피 추천 관련 상태
  const [recommendedRecipes, setRecommendedRecipes] = useState(''); // 추천 레시피 텍스트
  const [allergies, setAllergies] = useState(''); // 알레르기 입력
  const [preferences, setPreferences] = useState(''); // 선호도 입력
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태

  // --- 백엔드 API 기본 URL ---
  const API_BASE_URL = 'http://127.0.0.1:5000/api'; // Flask 백엔드 주소

  // --- 컴포넌트 마운트 시 로그인 상태 확인 및 재료 불러오기 ---
  useEffect(() => {
    if (token && userId) {
      setIsLoggedIn(true);
      setCurrentView('dashboard');
      fetchUserIngredients();
    }
  }, [token, userId]); // token 또는 userId가 변경될 때마다 실행

  // --- API 호출 헬퍼 함수 ---
  const callApi = async (endpoint, method, body = null) => {
    setMessage(''); // 메시지 초기화
    setIsLoading(true); // 로딩 시작
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const options = {
        method: method,
        headers: headers,
        body: body ? JSON.stringify(body) : null,
      };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || 'API 요청 실패');
      }
      return data;
    } catch (error) {
      console.error('API 호출 오류:', error);
      setMessage(`오류: ${error.message}`);
      return null;
    } finally {
      setIsLoading(false); // 로딩 종료
    }
  };

  // --- 사용자 인증 함수 ---
  const handleRegister = async (e) => {
    e.preventDefault();
    const data = await callApi('/register', 'POST', { username, email, password });
    if (data) {
      setMessage('회원가입 성공! 이제 로그인해주세요.');
      setCurrentView('login');
      setUsername('');
      setPassword('');
      setEmail('');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const data = await callApi('/login', 'POST', { username, password });
    if (data && data.token) {
      localStorage.setItem('jwtToken', data.token);
      localStorage.setItem('userId', data.user_id);
      setToken(data.token);
      setUserId(data.user_id);
      setIsLoggedIn(true);
      setMessage('로그인 성공!');
      setCurrentView('dashboard');
      fetchUserIngredients(); // 로그인 성공 시 재료 목록 불러오기
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('jwtToken');
    localStorage.removeItem('userId');
    setToken('');
    setUserId('');
    setIsLoggedIn(false);
    setMessage('로그아웃되었습니다.');
    setCurrentView('login');
    setIngredients([]);
    setRecommendedRecipes('');
  };

  // --- 재료 관리 함수 ---
  const fetchUserIngredients = async () => {
    if (!token) return;
    const data = await callApi('/user_ingredients', 'GET');
    if (data && data.ingredients) {
      setIngredients(data.ingredients);
    }
  };

  const handleAddIngredient = async (e) => {
    e.preventDefault();
    const data = await callApi('/user_ingredients', 'POST', {
      ingredient_name: newIngredientName,
      quantity: parseFloat(newIngredientQuantity),
      purchase_date: newIngredientPurchaseDate,
      expiration_date: newIngredientExpirationDate,
      location: newIngredientLocation,
    });
    if (data) {
      setMessage('재료가 성공적으로 추가되었습니다!');
      setNewIngredientName('');
      setNewIngredientQuantity('');
      setNewIngredientPurchaseDate('');
      setNewIngredientExpirationDate('');
      setNewIngredientLocation('냉장실');
      fetchUserIngredients(); // 재료 추가 후 목록 새로고침
      setCurrentView('dashboard'); // 대시보드로 돌아가기
    }
  };

  const handleDeleteIngredient = async (userIngredientId) => {
    if (window.confirm('정말로 이 재료를 삭제하시겠습니까?')) {
      const data = await callApi(`/user_ingredients/${userIngredientId}`, 'DELETE');
      if (data) {
        setMessage('재료가 성공적으로 삭제되었습니다.');
        fetchUserIngredients(); // 재료 삭제 후 목록 새로고침
      }
    }
  };

  // --- 레시피 추천 함수 ---
  const handleRecommendRecipes = async (e) => {
    e.preventDefault();
    const data = await callApi('/recommend_recipes', 'POST', {
      allergies: allergies.split(',').map(s => s.trim()).filter(Boolean),
      preferences: preferences.split(',').map(s => s.trim()).filter(Boolean),
    });
    if (data && data.recommended_recipes_text) {
      setRecommendedRecipes(data.recommended_recipes_text);
      setMessage('레시피 추천이 완료되었습니다!');
    }
  };

  // --- 뷰 렌더링 ---
  const renderView = () => {
    switch (currentView) {
      case 'login':
        return (
          <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">로그인</h2>
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="username">
                  사용자 이름
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="username"
                  type="text"
                  placeholder="사용자 이름을 입력하세요"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="password">
                  비밀번호
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
                  id="password"
                  type="password"
                  placeholder="비밀번호를 입력하세요"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <div className="flex items-center justify-between">
                <button
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-300 ease-in-out"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? '로그인 중...' : '로그인'}
                </button>
                <button
                  className="inline-block align-baseline font-bold text-sm text-blue-500 hover:text-blue-800 transition duration-300 ease-in-out"
                  type="button"
                  onClick={() => setCurrentView('register')}
                >
                  회원가입
                </button>
              </div>
            </form>
          </div>
        );
      case 'register':
        return (
          <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">회원가입</h2>
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="reg-username">
                  사용자 이름
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="reg-username"
                  type="text"
                  placeholder="사용자 이름을 입력하세요"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="reg-email">
                  이메일
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="reg-email"
                  type="email"
                  placeholder="이메일을 입력하세요"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="reg-password">
                  비밀번호
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
                  id="reg-password"
                  type="password"
                  placeholder="비밀번호를 입력하세요"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <div className="flex items-center justify-between">
                <button
                  className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-300 ease-in-out"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? '등록 중...' : '회원가입'}
                </button>
                <button
                  className="inline-block align-baseline font-bold text-sm text-green-500 hover:text-green-800 transition duration-300 ease-in-out"
                  type="button"
                  onClick={() => setCurrentView('login')}
                >
                  로그인 화면으로
                </button>
              </div>
            </form>
          </div>
        );
      case 'dashboard':
        return (
          <div className="w-full p-6 bg-white rounded-xl shadow-lg">
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">내 냉장고</h2>

            {/* 재료 목록 */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-700 mb-4">보유 재료 ({ingredients.length}개)</h3>
              {ingredients.length === 0 ? (
                <p className="text-gray-500 text-center">아직 재료가 없습니다. 재료를 추가해주세요!</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {ingredients.map((ing) => (
                    <div key={ing.user_ingredient_id} className="bg-gray-50 p-4 rounded-lg shadow-sm flex items-center justify-between">
                      <div>
                        <p className="font-bold text-lg text-gray-800">{ing.ingredient_name}</p>
                        <p className="text-sm text-gray-600">수량: {ing.quantity} {ing.unit || '개'}</p>
                        <p className="text-sm text-gray-600">유통기한: <span className={new Date(ing.expiration_date) < new Date() ? 'text-red-500 font-semibold' : 'text-green-600'}>{ing.expiration_date}</span></p>
                        <p className="text-sm text-gray-600">위치: {ing.location}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteIngredient(ing.user_ingredient_id)}
                        className="bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-3 rounded-lg text-sm transition duration-300 ease-in-out"
                      >
                        삭제
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 액션 버튼들 */}
            <div className="flex flex-wrap justify-center gap-4 mt-8">
              <button
                onClick={() => setCurrentView('addIngredient')}
                className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out"
              >
                + 재료 추가
              </button>
              <button
                onClick={() => setCurrentView('recommend')}
                className="bg-yellow-500 hover:bg-yellow-700 text-gray-800 font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out"
              >
                ✨ 레시피 추천받기
              </button>
            </div>
          </div>
        );
      case 'addIngredient':
        return (
          <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">재료 추가</h2>
            <form onSubmit={handleAddIngredient} className="space-y-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="ing-name">
                  재료 이름
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="ing-name"
                  type="text"
                  placeholder="예: 양파, 닭가슴살"
                  value={newIngredientName}
                  onChange={(e) => setNewIngredientName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="ing-quantity">
                  수량
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="ing-quantity"
                  type="number"
                  step="0.01"
                  placeholder="예: 2 (개), 500 (g)"
                  value={newIngredientQuantity}
                  onChange={(e) => setNewIngredientQuantity(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="ing-purchase-date">
                  구매일
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="ing-purchase-date"
                  type="date"
                  value={newIngredientPurchaseDate}
                  onChange={(e) => setNewIngredientPurchaseDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="ing-expiration-date">
                  유통기한
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="ing-expiration-date"
                  type="date"
                  value={newIngredientExpirationDate}
                  onChange={(e) => setNewIngredientExpirationDate(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="ing-location">
                  보관 위치
                </label>
                <select
                  className="shadow border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="ing-location"
                  value={newIngredientLocation}
                  onChange={(e) => setNewIngredientLocation(e.target.value)}
                >
                  <option value="냉장실">냉장실</option>
                  <option value="냉동실">냉동실</option>
                  <option value="상온">상온</option>
                  <option value="기타">기타</option>
                </select>
              </div>
              <div className="flex items-center justify-between mt-6">
                <button
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-300 ease-in-out"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? '추가 중...' : '재료 추가'}
                </button>
                <button
                  className="inline-block align-baseline font-bold text-sm text-gray-500 hover:text-gray-800 transition duration-300 ease-in-out"
                  type="button"
                  onClick={() => setCurrentView('dashboard')}
                >
                  취소
                </button>
              </div>
            </form>
          </div>
        );
      case 'recommend':
        return (
          <div className="w-full p-6 bg-white rounded-xl shadow-lg">
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">레시피 추천받기</h2>
            <form onSubmit={handleRecommendRecipes} className="space-y-4 mb-8">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="allergies">
                  알레르기 (콤마로 구분)
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="allergies"
                  type="text"
                  placeholder="예: 땅콩, 갑각류"
                  value={allergies}
                  onChange={(e) => setAllergies(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="preferences">
                  선호도 (콤마로 구분)
                </label>
                <input
                  className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="preferences"
                  type="text"
                  placeholder="예: 매운맛, 간단한 요리, 채식"
                  value={preferences}
                  onChange={(e) => setPreferences(e.target.value)}
                />
              </div>
              <div className="flex items-center justify-between">
                <button
                  className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-300 ease-in-out"
                  type="submit"
                  disabled={isLoading}
                >
                  {isLoading ? '추천 중...' : '레시피 추천받기'}
                </button>
                <button
                  className="inline-block align-baseline font-bold text-sm text-gray-500 hover:text-gray-800 transition duration-300 ease-in-out"
                  type="button"
                  onClick={() => setCurrentView('dashboard')}
                >
                  취소
                </button>
              </div>
            </form>

            {recommendedRecipes && (
              <div className="bg-gray-50 p-6 rounded-xl shadow-inner mt-8">
                <h3 className="text-xl font-semibold text-gray-700 mb-4">추천 레시피</h3>
                <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: recommendedRecipes.replace(/\n/g, '<br/>') }} />
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-purple-100 flex flex-col items-center justify-center p-4 font-sans">
      <header className="w-full max-w-3xl bg-white rounded-xl shadow-lg p-4 mb-8 flex justify-between items-center">
        <h1 className="text-3xl font-extrabold text-indigo-700">스마트 냉장고</h1>
        {isLoggedIn && (
          <nav className="flex space-x-4">
            <button
              onClick={() => { setCurrentView('dashboard'); fetchUserIngredients(); }}
              className={`py-2 px-4 rounded-lg font-semibold transition duration-300 ease-in-out ${currentView === 'dashboard' ? 'bg-indigo-600 text-white' : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'}`}
            >
              내 냉장고
            </button>
            <button
              onClick={() => setCurrentView('addIngredient')}
              className={`py-2 px-4 rounded-lg font-semibold transition duration-300 ease-in-out ${currentView === 'addIngredient' ? 'bg-indigo-600 text-white' : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'}`}
            >
              재료 추가
            </button>
            <button
              onClick={() => setCurrentView('recommend')}
              className={`py-2 px-4 rounded-lg font-semibold transition duration-300 ease-in-out ${currentView === 'recommend' ? 'bg-indigo-600 text-white' : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'}`}
            >
              레시피 추천
            </button>
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out"
            >
              로그아웃
            </button>
          </nav>
        )}
      </header>

      <main className="w-full max-w-3xl">
        {message && (
          <div className={`p-4 mb-4 rounded-lg text-center font-semibold ${message.startsWith('오류') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {message}
          </div>
        )}
        {renderView()}
      </main>
    </div>
  );
}

export default App;
