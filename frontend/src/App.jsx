import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import Nav from './components/Nav'
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
import { useLocalStorageState } from './utils/useLocalStorageState'
import { registerMember } from './api/client'

function AppInner() {
  const [user, setUser] = useLocalStorageState('nexus.user', null)
  const [enrolled, setEnrolled] = useLocalStorageState('nexus.enrolled', [])
  const { pathname } = useLocation()

  const isArticle = pathname.startsWith('/articles/')

  const finishOnboarding = async (nameOrData) => {
    const nickname = typeof nameOrData === 'string'
      ? (nameOrData || '김크레딧')
      : (nameOrData?.name || '김크레딧')
    const role = typeof nameOrData === 'object' ? nameOrData?.role : undefined
    const rawInterests = typeof nameOrData === 'object' ? nameOrData?.interests : undefined
    const interests = Array.isArray(rawInterests) ? rawInterests.join(', ') : rawInterests
    try {
      const member = await registerMember({ nickname, role, interests })
      setUser({ id: member.id, nickname: member.nickname, role: member.role })
    } catch {
      setUser({ id: null, nickname, role: role || null })
    }
  }

  const enroll = (classId) => {
    const progress = Math.floor(Math.random() * 25)
    setEnrolled(prev => [
      ...prev.filter(e => e.id !== classId),
      { id: classId, progress },
    ])
  }

  return (
    <div className="appbody">
      <Nav user={user} />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/curation" element={<Curation />} />
        <Route path="/articles/:id" element={<ArticleDetail />} />
        <Route path="/classes" element={<Classes />} />
        <Route path="/classes/:id" element={<ClassDetail enrolled={enrolled} onEnroll={enroll} />} />
        <Route path="/community" element={<Community user={user} setUser={setUser} />} />
        <Route path="/community/write" element={<CommunityWrite user={user} setUser={setUser} />} />
        <Route path="/community/:id" element={<CommunityDetail user={user} setUser={setUser} />} />
        <Route path="/meet" element={<Meet />} />
        <Route path="/meet/:id" element={<MeetDetail />} />
        <Route path="/hotdeal" element={<Hotdeal />} />
        <Route path="/onboarding" element={<Onboarding onFinish={finishOnboarding} />} />
        <Route path="/checkout/:classId" element={<Checkout onPay={finishOnboarding} />} />
        <Route path="/dashboard" element={<Dashboard user={user} enrolled={enrolled} />} />
      </Routes>
      {!isArticle && <Footer />}
      <MobileNav user={user} />
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
