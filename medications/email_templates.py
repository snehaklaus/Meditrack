def get_medication_reminder_email(user, medication):
    """Generate localized medication reminder email"""
    
    freq_display = medication.frequency.replace('_', ' ').title()
    
    # Hindi email
    if user.preferred_language == 'hi':
        subject = f"💊 {medication.name} लेने का समय"
        plain_message = (
            f"नमस्ते {user.username},\n\n"
            f"यह आपकी दवा लेने की याद दिलाता है:\n\n"
            f"दवा: {medication.name}\n"
            f"खुराक: {medication.dosage}\n"
            f"आवृत्ति: {freq_display}\n\n"
            f"स्वस्थ रहें!\n— मेडीट्रैक"
        )
        html_message = f"""
<!DOCTYPE html>
<html lang="hi">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#0891B2);border-radius:12px 12px 0 0;padding:28px 36px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">❤️ मेडीट्रैक</h1>
            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">दवा अनुस्मारक</p>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:28px 36px;">
            <p style="margin:0 0 20px;color:#0F172A;font-size:15px;">
              नमस्ते <strong>{user.username}</strong>, अपनी दवा लेने का समय!
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#EFF6FF;border-radius:10px;border:1px solid #BFDBFE;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 4px;font-size:11px;color:#2563EB;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
                    दवा
                  </p>
                  <p style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0F172A;">
                    💊 {medication.name}
                  </p>
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">खुराक</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{medication.dosage}</p>
                      </td>
                      <td width="4%"></td>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">आवृत्ति</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{freq_display}</p>
                      </td>
                    </tr>
                  </table>
                  {f'<p style="margin:12px 0 0;font-size:13px;color:#475569;font-style:italic;">{medication.notes}</p>' if medication.notes else ''}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:0 36px 28px;text-align:center;">
            <a href="https://meditrack7.vercel.app"
               style="display:inline-block;background:linear-gradient(135deg,#2563EB,#0891B2);
                      color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;
                      padding:12px 28px;border-radius:8px;">
              मेडीट्रैक खोलें →
            </a>
          </td>
        </tr>
        <tr>
          <td style="background:#F8FAFC;border-top:1px solid #E2E8F0;border-radius:0 0 12px 12px;
                     padding:16px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#94A3B8;">
              आप यह प्राप्त कर रहे हैं क्योंकि मेडीट्रैक पर आपके पास एक सक्रिय दवा अनुस्मारक है।
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
        """
    
    # English email (original)
    else:
        subject = f"💊 Time to take {medication.name}"
        plain_message = (
            f"Hi {user.username},\n\n"
            f"This is a reminder to take your medication:\n\n"
            f"Medication: {medication.name}\n"
            f"Dosage: {medication.dosage}\n"
            f"Frequency: {freq_display}\n\n"
            f"Stay healthy!\n— MediTrack"
        )
        html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#0891B2);border-radius:12px 12px 0 0;padding:28px 36px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">❤️ MediTrack</h1>
            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">Medication Reminder</p>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:28px 36px;">
            <p style="margin:0 0 20px;color:#0F172A;font-size:15px;">
              Hi <strong>{user.username}</strong>, time to take your medication!
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#EFF6FF;border-radius:10px;border:1px solid #BFDBFE;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 4px;font-size:11px;color:#2563EB;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
                    Medication
                  </p>
                  <p style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0F172A;">
                    💊 {medication.name}
                  </p>
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">DOSAGE</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{medication.dosage}</p>
                      </td>
                      <td width="4%"></td>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">FREQUENCY</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{freq_display}</p>
                      </td>
                    </tr>
                  </table>
                  {f'<p style="margin:12px 0 0;font-size:13px;color:#475569;font-style:italic;">{medication.notes}</p>' if medication.notes else ''}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#ffffff;padding:0 36px 28px;text-align:center;">
            <a href="https://meditrack7.vercel.app"
               style="display:inline-block;background:linear-gradient(135deg,#2563EB,#0891B2);
                      color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;
                      padding:12px 28px;border-radius:8px;">
              Open MediTrack →
            </a>
          </td>
        </tr>
        <tr>
          <td style="background:#F8FAFC;border-top:1px solid #E2E8F0;border-radius:0 0 12px 12px;
                     padding:16px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#94A3B8;">
              You're receiving this because you have an active medication reminder on MediTrack.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
        """
    
    return subject, plain_message, html_message