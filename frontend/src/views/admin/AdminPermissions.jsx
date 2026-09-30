import { useCallback, useEffect, useState } from 'react'
import { fetchAdminMembers, updateMemberAccess } from '../../api/client'

export default function AdminPermissions() {
  const [members, setMembers] = useState([])
  const [drafts, setDrafts] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const list = await fetchAdminMembers()
      setMembers(list)
      setDrafts(Object.fromEntries(list.map(item => [item.id, item.accessRole])))
    } catch (err) {
      setError(err.message || '회원 목록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const changed = members.filter(member => drafts[member.id] !== member.accessRole)

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      let next = members
      for (const member of changed) {
        const updated = await updateMemberAccess(member.id, drafts[member.id])
        next = next.map(item => (item.id === updated.id ? updated : item))
      }
      setMembers(next)
      setDrafts(Object.fromEntries(next.map(item => [item.id, item.accessRole])))
    } catch (err) {
      setError(err.message || '권한을 바꾸지 못했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <h1 className="admin-title">권한관리</h1>
      <p className="admin-lead">어드민으로 바꾸면 그 회원이 큐레이션 글을 쓸 수 있습니다.</p>
      {error && <p role="alert" className="admin-error">{error}</p>}
      {loading ? <p className="admin-lead">불러오는 중...</p> : (
        <>
          <table className="admin-table">
            <thead>
              <tr><th>닉네임</th><th>권한</th></tr>
            </thead>
            <tbody>
              {members.map(member => (
                <tr key={member.id}>
                  <td>{member.nickname}</td>
                  <td>
                    <select
                      aria-label={`${member.nickname} 권한`}
                      value={drafts[member.id] || member.accessRole}
                      onChange={(event) => setDrafts(current => ({
                        ...current,
                        [member.id]: event.target.value,
                      }))}
                    >
                      <option value="user">사용자</option>
                      <option value="admin">어드민</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="admin-save-row">
            <button
              type="button"
              className="admin-publish"
              onClick={save}
              disabled={saving || changed.length === 0}
            >
              {saving ? '저장 중...' : '저장'}
            </button>
          </div>
        </>
      )}
    </section>
  )
}
