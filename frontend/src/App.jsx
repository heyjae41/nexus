import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import Nav from './components/Nav'
import AuthModal from './components/AuthModal'
import Footer from './components/Footer'
import MobileNav from './components/MobileNav'
import Home from './views/Home'
import Curation from './views/Curation'
import ArticleDetail from './views/ArticleDetail'
import Classes from './views/Classes'
import ClassDetail from './views/ClassDetail'
import Community from './views/Community'
import CommunityDetail from './views/CommunityDetail'
import CommunityWrite from './views/CommunityWrite'
import Meet from './views/Meet'
import MeetDetail from './views/MeetDetail'
import Hotdeal from './views/Hotdeal'
import Onboarding from './views/Onboarding'
import Checkout from './views/Checkout'
import Dashboard from './views/Dashboard'
import Profile from './views/Profile'
import { useLocalStorageState } from './utils/useLocalStorageState'
import { fetchCurrentMember, logoutMember, registerAccount } from './api/client'

function AppInner() {
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)
  const [enrolled, setEnrolled] = useLocalStorageState('nexus.enrolled', [])
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const isArticle = pathname.startsWith('/articles/')

  useEffect(() => {
    let active = true
    localStorage.removeItem('nexus.user')
    fetchCurrentMember()
      .then(member => { if (active) setUser(member) })
      .catch(() => { if (active) setUser(null) })
      .finally(() => { if (active) setAuthReady(true) })
    return () => { active = false }
  }, [])

  const finishOnboarding = async ({ name, password, role, interests } = {}) => {
    const member = await registerAccount({
      nickname: name,
      password,
      role,
      interests,
    })
    setUser(member)
    return member
  }

  const logout = async () => {
    await logoutMember()
    localStorage.removeItem('nexus.user')
    localStorage.removeItem('nexus.enrolled')
    setUser(null)
    setLoginOpen(false)
    navigate('/', { replace: true })
  }

  const enroll = (classId) => {
    const progress = Math.floor(Math.random() * 25)
    setEnrolled(prev => [
      ...prev.filter(e => e.id !== classId),
      { id: classId, progress },
    ])
  }

  if (!authReady) {
    return <main style={{ minHeight: '60vh', display: 'grid', placeItems: 'center', color: '#9a9aa4' }}>세션 확인 중...</main>
  }

  return (
    <div className="appbody">
      <Nav user={user} onLogin={() => setLoginOpen(true)} onLogout={logout} />
      <AuthModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        onAuthenticated={setUser}
        onSignup={() => { setLoginOpen(false); navigate('/onboarding') }}
      />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/curation" element={<Curation />} />
        <Route path="/articles/:id" element={<ArticleDetail />} />
        <Route path="/classes" element={<Classes />} />
        <Route path="/classes/:id" element={<ClassDetail user={user} enrolled={enrolled} onEnroll={enroll} />} />
        <Route path="/community" element={<Community user={user} setUser={setUser} />} />
        <Route path="/community/write" element={<CommunityWrite user={user} setUser={setUser} />} />
        <Route path="/community/:id" element={<CommunityDetail user={user} setUser={setUser} />} />
        <Route path="/meet" element={<Meet />} />
        <Route path="/meet/:id" element={<MeetDetail />} />
        <Route path="/hotdeal" element={<Hotdeal />} />
        <Route path="/onboarding" element={<Onboarding onFinish={finishOnboarding} />} />
        <Route path="/checkout/:classId" element={<Checkout />} />
        <Route path="/dashboard" element={<Dashboard user={user} enrolled={enrolled} />} />
        <Route path="/profile" element={<Profile user={user} setUser={setUser} />} />
      </Routes>
      {!isArticle && <Footer />}
      <MobileNav user={user} onLogin={() => setLoginOpen(true)} />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  )
}
