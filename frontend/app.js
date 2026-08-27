document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiStatus = document.getElementById('api-status');
    const extractForm = document.getElementById('extract-form');
    const profileUrlInput = document.getElementById('profile-url');
    const submitBtn = document.getElementById('submit-btn');
    const loader = document.getElementById('loader');
    const errorCard = document.getElementById('error-card');
    const errorMessage = document.getElementById('error-message');
    const closeErrBtn = document.getElementById('close-err-btn');
    const resultsSection = document.getElementById('results-section');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Status loader steps
    const stepConnect = document.getElementById('step-connect');
    const stepScrape = document.getElementById('step-scrape');
    const stepParse = document.getElementById('step-parse');

    // Visual profile components
    const profileAvatar = document.getElementById('profile-avatar');
    const avatarFallback = document.querySelector('.avatar-fallback');
    const profileName = document.getElementById('profile-name');
    const profileUrnTag = document.getElementById('profile-urn-tag');
    const profileHeadline = document.getElementById('profile-headline');
    const profileLocation = document.getElementById('profile-location');
    const profileEmail = document.getElementById('profile-email');
    const metaEmailContainer = document.getElementById('meta-email-container');
    const profileSummary = document.getElementById('profile-summary');
    const sectionAbout = document.getElementById('section-about');
    
    const experienceList = document.getElementById('experience-list');
    const sectionExperience = document.getElementById('section-experience');
    
    const educationList = document.getElementById('education-list');
    const sectionEducation = document.getElementById('section-education');
    
    const skillsList = document.getElementById('skills-list');
    const sectionSkills = document.getElementById('section-skills');
    
    const certificationsList = document.getElementById('certifications-list');
    const sectionCertifications = document.getElementById('section-certifications');
    
    const languagesList = document.getElementById('languages-list');
    const sectionLanguages = document.getElementById('section-languages');
    
    // JSON viewer components
    const jsonCodeBlock = document.getElementById('json-code-block');
    const copyJsonBtn = document.getElementById('copy-json-btn');

    let extractedData = null;

    // Check API Health on load
    checkApiHealth();

    // Tab Switching Logic
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');
            
            // Toggle active tab buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Toggle active tab content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTab) {
                    content.classList.add('active');
                }
            });
        });
    });

    // Handle Form Submission
    extractForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const profileUrl = profileUrlInput.value.trim();
        if (!profileUrl) return;

        // Reset UI States
        errorCard.classList.add('hidden');
        resultsSection.classList.add('hidden');
        loader.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.7';

        // Update loader animation steps
        setLoaderStep(stepConnect, 'active', '<i class="fa-solid fa-circle-notch fa-spin"></i> Connecting to API server...');
        setLoaderStep(stepScrape, 'pending', '<i class="fa-regular fa-circle"></i> Fetching profile from LinkedIn...');
        setLoaderStep(stepParse, 'pending', '<i class="fa-regular fa-circle"></i> Parsing and structuring payload...');

        try {
            // Step 1: Simulated network delay to show step 1, then proceed
            await delay(600);
            setLoaderStep(stepConnect, 'done', '<i class="fa-solid fa-circle-check"></i> Connected to API server');
            setLoaderStep(stepScrape, 'active', '<i class="fa-solid fa-circle-notch fa-spin"></i> Querying LinkedIn identity components...');

            // Fetch API request
            const response = await fetch(`/api/v1/profile?profile_url=${encodeURIComponent(profileUrl)}`);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to extract profile. Please ensure session cookies are active.');
            }

            setLoaderStep(stepScrape, 'done', '<i class="fa-solid fa-circle-check"></i> Profile fetched successfully');
            setLoaderStep(stepParse, 'active', '<i class="fa-solid fa-circle-notch fa-spin"></i> Normalizing data layout...');
            
            await delay(500); // Visual transition
            setLoaderStep(stepParse, 'done', '<i class="fa-solid fa-circle-check"></i> Data normalization complete');

            extractedData = result.data;
            
            // Render Profile and JSON Views
            renderProfile(extractedData);
            renderJsonView(extractedData);
            
            // Display Dashboard Results
            loader.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            
            // Auto switch to visual tab
            tabButtons[0].click();
            
            // Scroll results into view smoothly
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (err) {
            console.error(err);
            loader.classList.add('hidden');
            errorMessage.textContent = err.message || 'An unexpected error occurred. Please try again.';
            errorCard.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
        }
    });

    // Close Error Card
    closeErrBtn.addEventListener('click', () => {
        errorCard.classList.add('hidden');
    });

    // Copy JSON to Clipboard
    copyJsonBtn.addEventListener('click', () => {
        if (!extractedData) return;
        
        const jsonText = JSON.stringify(extractedData, null, 2);
        navigator.clipboard.writeText(jsonText).then(() => {
            // Update button UI feedback
            const originalHTML = copyJsonBtn.innerHTML;
            copyJsonBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Copied!</span>';
            copyJsonBtn.classList.add('success');
            
            setTimeout(() => {
                copyJsonBtn.innerHTML = originalHTML;
                copyJsonBtn.classList.remove('success');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    });

    // Helper functions

    async function checkApiHealth() {
        const indicator = apiStatus.querySelector('.status-indicator');
        const label = apiStatus.querySelector('.status-label');
        
        try {
            const res = await fetch('/health');
            const data = await res.json();
            
            indicator.className = 'status-indicator online';
            
            if (data.cookies_configured) {
                label.textContent = 'API Server Online';
            } else {
                label.textContent = 'API Config Required';
                label.style.color = 'var(--warning)';
                showConfigWarning();
            }
        } catch (err) {
            indicator.className = 'status-indicator offline';
            label.textContent = 'API Server Offline';
            console.warn('API Health check failed: ', err);
        }
    }

    function showConfigWarning() {
        errorMessage.innerHTML = '<strong>Server Configuration Warning:</strong> LinkedIn cookies (LI_AT and JSESSIONID) are not configured in the server `.env` file. The API will return errors until configured.';
        errorCard.classList.remove('hidden');
    }

    function setLoaderStep(element, status, text) {
        element.innerHTML = text;
        element.className = 'step';
        if (status === 'active') {
            element.classList.add('active');
        } else if (status === 'done') {
            element.classList.add('done');
        }
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function renderProfile(data) {
        // Basic Info
        profileName.textContent = data.full_name || 'No Name';
        profileHeadline.textContent = data.headline || 'No Headline';
        profileLocation.textContent = data.location || 'Unknown Location';
        
        if (data.urn_id) {
            profileUrnTag.textContent = `urn:li:fs_profile:${data.urn_id}`;
            profileUrnTag.classList.remove('hidden');
        } else {
            profileUrnTag.classList.add('hidden');
        }

        // Profile Picture
        if (data.profile_picture_url) {
            profileAvatar.src = data.profile_picture_url;
            profileAvatar.classList.remove('hidden');
            avatarFallback.classList.add('hidden');
        } else {
            profileAvatar.classList.add('hidden');
            avatarFallback.classList.remove('hidden');
        }

        // Contact info
        const email = data.contact_info?.email;
        if (email) {
            profileEmail.textContent = email;
            metaEmailContainer.classList.remove('hidden');
        } else {
            metaEmailContainer.classList.add('hidden');
        }

        // Summary/About
        if (data.summary) {
            profileSummary.textContent = data.summary;
            sectionAbout.classList.remove('hidden');
        } else {
            sectionAbout.classList.add('hidden');
        }

        // Experience
        if (data.experience && data.experience.length > 0) {
            experienceList.innerHTML = data.experience.map(exp => {
                const logoHtml = exp.company_logo_url 
                    ? `<img src="${exp.company_logo_url}" alt="${exp.company || 'Company'} Logo">`
                    : `<div class="logo-placeholder"><i class="fa-solid fa-briefcase"></i></div>`;
                
                const companyLink = exp.company_url 
                    ? `<a href="${exp.company_url}" target="_blank">${exp.company || 'Unknown Company'}</a>`
                    : `<span>${exp.company || 'Unknown Company'}</span>`;

                return `
                    <div class="timeline-item">
                        <div class="timeline-content">
                            <div class="logo-container">
                                ${logoHtml}
                            </div>
                            <div class="timeline-body">
                                <div class="timeline-title-row">
                                    <h4>${exp.title || 'No Position Title'}</h4>
                                    <span class="timeline-date-badge">${exp.start_date || ''} - ${exp.end_date || 'Present'}</span>
                                </div>
                                <p class="timeline-company">${companyLink}</p>
                                <div class="timeline-meta">
                                    ${exp.location ? `<span><i class="fa-solid fa-location-dot"></i> ${exp.location}</span>` : ''}
                                    ${exp.duration ? `<span><i class="fa-regular fa-clock"></i> ${exp.duration}</span>` : ''}
                                </div>
                                ${exp.description ? `<p class="timeline-description">${exp.description}</p>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            sectionExperience.classList.remove('hidden');
        } else {
            sectionExperience.classList.add('hidden');
        }

        // Education
        if (data.education && data.education.length > 0) {
            educationList.innerHTML = data.education.map(edu => {
                const logoHtml = edu.school_logo_url 
                    ? `<img src="${edu.school_logo_url}" alt="${edu.school || 'School'} Logo">`
                    : `<div class="logo-placeholder"><i class="fa-solid fa-graduation-cap"></i></div>`;

                const schoolLink = edu.school_url 
                    ? `<a href="${edu.school_url}" target="_blank">${edu.school || 'Unknown School'}</a>`
                    : `<span>${edu.school || 'Unknown School'}</span>`;

                const degreeText = [edu.degree, edu.field_of_study].filter(Boolean).join(', ');

                return `
                    <div class="timeline-item">
                        <div class="timeline-content">
                            <div class="logo-container">
                                ${logoHtml}
                            </div>
                            <div class="timeline-body">
                                <div class="timeline-title-row">
                                    <h4>${schoolLink}</h4>
                                    <span class="timeline-date-badge">
                                        ${[edu.start_date, edu.end_date].filter(Boolean).join(' - ') || 'No Date Info'}
                                    </span>
                                </div>
                                ${degreeText ? `<p class="timeline-company">${degreeText}</p>` : ''}
                                ${edu.description ? `<p class="timeline-description">${edu.description}</p>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            sectionEducation.classList.remove('hidden');
        } else {
            sectionEducation.classList.add('hidden');
        }

        // Skills
        if (data.skills && data.skills.length > 0) {
            skillsList.innerHTML = data.skills.map(skill => `
                <span class="skill-pill">${skill}</span>
            `).join('');
            sectionSkills.classList.remove('hidden');
        } else {
            sectionSkills.classList.add('hidden');
        }

        // Certifications
        if (data.certifications && data.certifications.length > 0) {
            certificationsList.innerHTML = data.certifications.map(cert => {
                const certLink = cert.url 
                    ? `<a href="${cert.url}" target="_blank">${cert.name} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.8rem;"></i></a>`
                    : `<span>${cert.name}</span>`;
                
                const certDate = [cert.start_date, cert.end_date].filter(Boolean).join(' - ');

                return `
                    <div class="cert-card">
                        <div class="cert-icon-wrapper">
                            <i class="fa-solid fa-award"></i>
                        </div>
                        <div class="cert-details">
                            <h4>${certLink}</h4>
                            <p class="cert-meta">
                                <span class="cert-authority">${cert.authority || ''}</span>
                                ${certDate ? ` • <span>${certDate}</span>` : ''}
                                ${cert.license_number ? ` • <span>ID: ${cert.license_number}</span>` : ''}
                            </p>
                        </div>
                    </div>
                `;
            }).join('');
            sectionCertifications.classList.remove('hidden');
        } else {
            sectionCertifications.classList.add('hidden');
        }

        // Languages
        if (data.languages && data.languages.length > 0) {
            languagesList.innerHTML = data.languages.map(lang => {
                const prof = lang.proficiency 
                    ? lang.proficiency.replace(/_/g, ' ').toLowerCase() 
                    : 'proficiency unspecified';
                return `
                    <div class="lang-card">
                        <span class="lang-name">${lang.name}</span>
                        <span class="lang-proficiency">${prof}</span>
                    </div>
                `;
            }).join('');
            sectionLanguages.classList.remove('hidden');
        } else {
            sectionLanguages.classList.add('hidden');
        }
    }

    function renderJsonView(data) {
        // Stringify JSON with nice spacing indent of 2
        jsonCodeBlock.textContent = JSON.stringify(data, null, 2);
    }
});
